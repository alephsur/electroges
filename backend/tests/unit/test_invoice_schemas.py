"""
Unit tests for invoice Pydantic schemas.

Pure Python — no database, no mocks, no async.
Covers:
  - PaymentCreate validation (amount > 0, required fields)
  - InvoiceLineCreate validation (quantity/unit_price constraints, discount range)
  - InvoiceLineUpdate partial update semantics
  - InvoiceFromWorkOrderRequest requires at least one source
  - RectificationRequest reason min-length
  - InvoiceTotals structure
  - InvoiceFilters defaults
  - ReorderLinesRequest
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceFilters,
    InvoiceFromWorkOrderRequest,
    InvoiceLineCreate,
    InvoiceLineResponse,
    InvoiceLineUpdate,
    InvoiceTotals,
    InvoiceUpdate,
    PaymentCreate,
    PaymentReminderResponse,
    PaymentResponse,
    RectificationRequest,
    ReorderLinesRequest,
)

_TODAY = date(2025, 6, 15)
_NOW = datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc)


# ── PaymentCreate ──────────────────────────────────────────────────────────────

class TestPaymentCreate:
    def test_valid_transfer_payment(self):
        p = PaymentCreate(
            amount=Decimal("500.00"),
            payment_date=_TODAY,
            method="transfer",
        )
        assert p.amount == Decimal("500.00")
        assert p.method == "transfer"
        assert p.reference is None
        assert p.notes is None

    def test_all_payment_methods_accepted(self):
        for method in ("transfer", "cash", "card", "direct_debit"):
            p = PaymentCreate(amount=Decimal("1"), payment_date=_TODAY, method=method)
            assert p.method == method

    def test_amount_must_be_positive(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount=Decimal("0"), payment_date=_TODAY, method="cash")

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount=Decimal("-10"), payment_date=_TODAY, method="cash")

    def test_invalid_method_rejected(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount=Decimal("100"), payment_date=_TODAY, method="bitcoin")

    def test_optional_reference_and_notes(self):
        p = PaymentCreate(
            amount=Decimal("250"),
            payment_date=_TODAY,
            method="transfer",
            reference="TRF-001",
            notes="Pago parcial primera entrega",
        )
        assert p.reference == "TRF-001"
        assert p.notes == "Pago parcial primera entrega"

    def test_payment_date_required(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount=Decimal("100"), method="cash")


# ── InvoiceLineCreate ──────────────────────────────────────────────────────────

class TestInvoiceLineCreate:
    def test_valid_manual_line(self):
        line = InvoiceLineCreate(
            description="Instalación cuadro eléctrico",
            quantity=Decimal("1"),
            unit_price=Decimal("350.00"),
        )
        assert line.origin_type == "manual"
        assert line.line_discount_pct == Decimal("0.00")
        assert line.sort_order == 0
        assert line.origin_id is None

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            InvoiceLineCreate(description="Cable", quantity=Decimal("0"), unit_price=Decimal("10"))

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            InvoiceLineCreate(description="Cable", quantity=Decimal("-1"), unit_price=Decimal("10"))

    def test_unit_price_zero_accepted(self):
        line = InvoiceLineCreate(description="Garantía", quantity=Decimal("1"), unit_price=Decimal("0"))
        assert line.unit_price == Decimal("0")

    def test_negative_unit_price_rejected(self):
        with pytest.raises(ValidationError):
            InvoiceLineCreate(description="Item", quantity=Decimal("1"), unit_price=Decimal("-5"))

    def test_discount_pct_zero_to_hundred_accepted(self):
        for pct in ("0", "50", "100"):
            line = InvoiceLineCreate(
                description="Item", quantity=Decimal("1"),
                unit_price=Decimal("100"), line_discount_pct=Decimal(pct),
            )
            assert line.line_discount_pct == Decimal(pct)

    def test_discount_pct_above_hundred_rejected(self):
        with pytest.raises(ValidationError):
            InvoiceLineCreate(
                description="Item", quantity=Decimal("1"),
                unit_price=Decimal("100"), line_discount_pct=Decimal("101"),
            )

    def test_negative_discount_pct_rejected(self):
        with pytest.raises(ValidationError):
            InvoiceLineCreate(
                description="Item", quantity=Decimal("1"),
                unit_price=Decimal("100"), line_discount_pct=Decimal("-1"),
            )

    def test_certification_origin_type(self):
        cert_id = uuid.uuid4()
        line = InvoiceLineCreate(
            origin_type="certification",
            origin_id=cert_id,
            description="Certificación obra 1",
            quantity=Decimal("1"),
            unit_price=Decimal("1200.00"),
        )
        assert line.origin_type == "certification"
        assert line.origin_id == cert_id

    def test_task_origin_type(self):
        task_id = uuid.uuid4()
        line = InvoiceLineCreate(
            origin_type="task",
            origin_id=task_id,
            description="Tarea completada",
            quantity=Decimal("1"),
            unit_price=Decimal("400.00"),
        )
        assert line.origin_type == "task"

    def test_invalid_origin_type_rejected(self):
        with pytest.raises(ValidationError):
            InvoiceLineCreate(
                origin_type="budget",
                description="X",
                quantity=Decimal("1"),
                unit_price=Decimal("100"),
            )

    def test_optional_unit_field(self):
        line = InvoiceLineCreate(
            description="Cable", quantity=Decimal("10"),
            unit_price=Decimal("2.50"), unit="m",
        )
        assert line.unit == "m"

    def test_description_required(self):
        with pytest.raises(ValidationError):
            InvoiceLineCreate(quantity=Decimal("1"), unit_price=Decimal("100"))


# ── InvoiceLineUpdate ──────────────────────────────────────────────────────────

class TestInvoiceLineUpdate:
    def test_all_fields_optional(self):
        data = InvoiceLineUpdate()
        assert data.model_fields_set == set()

    def test_partial_update_tracks_set_fields(self):
        data = InvoiceLineUpdate(unit_price=Decimal("150.00"))
        assert "unit_price" in data.model_fields_set
        assert "quantity" not in data.model_fields_set

    def test_model_dump_exclude_none_partial(self):
        data = InvoiceLineUpdate(description="Nueva descripción", sort_order=2)
        dumped = data.model_dump(exclude_none=True)
        assert dumped == {"description": "Nueva descripción", "sort_order": 2}

    def test_model_dump_exclude_unset_partial(self):
        data = InvoiceLineUpdate(quantity=Decimal("5"))
        dumped = data.model_dump(exclude_unset=True)
        assert set(dumped.keys()) == {"quantity"}


# ── InvoiceCreate ──────────────────────────────────────────────────────────────

class TestInvoiceCreate:
    def test_minimum_valid_invoice(self):
        customer_id = uuid.uuid4()
        inv = InvoiceCreate(customer_id=customer_id)
        assert inv.customer_id == customer_id
        assert inv.work_order_id is None
        assert inv.discount_pct == Decimal("0.00")
        assert inv.lines == []

    def test_with_lines(self):
        customer_id = uuid.uuid4()
        inv = InvoiceCreate(
            customer_id=customer_id,
            lines=[
                InvoiceLineCreate(description="Item 1", quantity=Decimal("2"), unit_price=Decimal("50")),
                InvoiceLineCreate(description="Item 2", quantity=Decimal("1"), unit_price=Decimal("100")),
            ],
        )
        assert len(inv.lines) == 2

    def test_discount_pct_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            InvoiceCreate(customer_id=uuid.uuid4(), discount_pct=Decimal("-1"))

    def test_discount_pct_max_100(self):
        with pytest.raises(ValidationError):
            InvoiceCreate(customer_id=uuid.uuid4(), discount_pct=Decimal("101"))

    def test_customer_id_required(self):
        with pytest.raises(ValidationError):
            InvoiceCreate()


# ── InvoiceFromWorkOrderRequest ────────────────────────────────────────────────

class TestInvoiceFromWorkOrderRequest:
    def test_raises_when_no_source_provided(self):
        with pytest.raises(ValidationError) as exc_info:
            InvoiceFromWorkOrderRequest(work_order_id=uuid.uuid4())
        assert "certificación" in str(exc_info.value).lower() or "tarea" in str(exc_info.value).lower()

    def test_valid_with_certification_ids(self):
        req = InvoiceFromWorkOrderRequest(
            work_order_id=uuid.uuid4(),
            certification_ids=[uuid.uuid4()],
        )
        assert len(req.certification_ids) == 1

    def test_valid_with_task_ids(self):
        req = InvoiceFromWorkOrderRequest(
            work_order_id=uuid.uuid4(),
            task_ids=[uuid.uuid4(), uuid.uuid4()],
        )
        assert len(req.task_ids) == 2

    def test_valid_with_extra_lines(self):
        req = InvoiceFromWorkOrderRequest(
            work_order_id=uuid.uuid4(),
            extra_lines=[
                InvoiceLineCreate(description="Línea manual", quantity=Decimal("1"), unit_price=Decimal("200"))
            ],
        )
        assert len(req.extra_lines) == 1

    def test_valid_with_all_sources_combined(self):
        req = InvoiceFromWorkOrderRequest(
            work_order_id=uuid.uuid4(),
            certification_ids=[uuid.uuid4()],
            task_ids=[uuid.uuid4()],
            extra_lines=[
                InvoiceLineCreate(description="Extra", quantity=Decimal("1"), unit_price=Decimal("50"))
            ],
        )
        assert len(req.certification_ids) == 1
        assert len(req.task_ids) == 1
        assert len(req.extra_lines) == 1

    def test_discount_pct_defaults_to_zero(self):
        req = InvoiceFromWorkOrderRequest(
            work_order_id=uuid.uuid4(),
            task_ids=[uuid.uuid4()],
        )
        assert req.discount_pct == Decimal("0.00")

    def test_work_order_id_required(self):
        with pytest.raises(ValidationError):
            InvoiceFromWorkOrderRequest(task_ids=[uuid.uuid4()])


# ── InvoiceUpdate ──────────────────────────────────────────────────────────────

class TestInvoiceUpdate:
    def test_all_fields_optional(self):
        data = InvoiceUpdate()
        assert data.model_fields_set == set()

    def test_partial_update(self):
        data = InvoiceUpdate(notes="Nota actualizada")
        assert data.notes == "Nota actualizada"
        assert "notes" in data.model_fields_set
        assert "tax_rate" not in data.model_fields_set

    def test_model_dump_exclude_none(self):
        data = InvoiceUpdate(issue_date=_TODAY, due_date=date(2025, 7, 15))
        dumped = data.model_dump(exclude_none=True)
        assert set(dumped.keys()) == {"issue_date", "due_date"}


# ── RectificationRequest ───────────────────────────────────────────────────────

class TestRectificationRequest:
    def test_valid_reason_minimum_length(self):
        req = RectificationRequest(reason="Error")
        assert req.reason == "Error"
        assert req.notes is None

    def test_reason_too_short_rejected(self):
        with pytest.raises(ValidationError):
            RectificationRequest(reason="No")

    def test_reason_exactly_five_chars_accepted(self):
        req = RectificationRequest(reason="12345")
        assert len(req.reason) == 5

    def test_optional_notes(self):
        req = RectificationRequest(
            reason="Precio incorrecto en factura",
            notes="Comunicado al cliente el 15/06",
        )
        assert req.notes == "Comunicado al cliente el 15/06"

    def test_reason_required(self):
        with pytest.raises(ValidationError):
            RectificationRequest()


# ── InvoiceTotals ──────────────────────────────────────────────────────────────

class TestInvoiceTotals:
    def _make_totals(self, **kwargs) -> InvoiceTotals:
        defaults = dict(
            subtotal_before_discount=Decimal("1000.00"),
            discount_amount=Decimal("0.00"),
            taxable_base=Decimal("1000.00"),
            tax_amount=Decimal("210.00"),
            total=Decimal("1210.00"),
            total_paid=Decimal("0.00"),
            pending_amount=Decimal("1210.00"),
            is_fully_paid=False,
        )
        defaults.update(kwargs)
        return InvoiceTotals(**defaults)

    def test_standard_totals(self):
        t = self._make_totals()
        assert t.total == Decimal("1210.00")
        assert t.is_fully_paid is False

    def test_fully_paid_flag(self):
        t = self._make_totals(
            total_paid=Decimal("1210.00"),
            pending_amount=Decimal("0.00"),
            is_fully_paid=True,
        )
        assert t.is_fully_paid is True
        assert t.pending_amount == Decimal("0.00")

    def test_partial_payment(self):
        t = self._make_totals(
            total_paid=Decimal("600.00"),
            pending_amount=Decimal("610.00"),
            is_fully_paid=False,
        )
        assert t.total_paid == Decimal("600.00")
        assert t.pending_amount == Decimal("610.00")

    def test_with_discount(self):
        t = self._make_totals(
            subtotal_before_discount=Decimal("1000.00"),
            discount_amount=Decimal("100.00"),
            taxable_base=Decimal("900.00"),
            tax_amount=Decimal("189.00"),
            total=Decimal("1089.00"),
            pending_amount=Decimal("1089.00"),
        )
        assert t.taxable_base == Decimal("900.00")
        assert t.total == Decimal("1089.00")


# ── InvoiceLineResponse ────────────────────────────────────────────────────────

class TestInvoiceLineResponse:
    def test_subtotal_field_present(self):
        line = InvoiceLineResponse(
            id=uuid.uuid4(),
            invoice_id=uuid.uuid4(),
            origin_type="manual",
            origin_id=None,
            sort_order=0,
            description="Trabajo",
            quantity=Decimal("2"),
            unit=None,
            unit_price=Decimal("100.00"),
            line_discount_pct=Decimal("0.00"),
            subtotal=Decimal("200.00"),
        )
        assert line.subtotal == Decimal("200.00")

    def test_subtotal_with_line_discount(self):
        # quantity=10, unit_price=100, discount=10% → subtotal=900
        line = InvoiceLineResponse(
            id=uuid.uuid4(),
            invoice_id=uuid.uuid4(),
            origin_type="manual",
            origin_id=None,
            sort_order=1,
            description="Cable con descuento",
            quantity=Decimal("10"),
            unit="m",
            unit_price=Decimal("100.00"),
            line_discount_pct=Decimal("10.00"),
            subtotal=Decimal("900.00"),
        )
        assert line.subtotal == Decimal("900.00")


# ── InvoiceFilters ─────────────────────────────────────────────────────────────

class TestInvoiceFilters:
    def test_defaults(self):
        f = InvoiceFilters()
        assert f.skip == 0
        assert f.limit == 50
        assert f.overdue_only is False
        assert f.q is None
        assert f.customer_id is None
        assert f.status is None

    def test_custom_pagination(self):
        f = InvoiceFilters(skip=100, limit=25)
        assert f.skip == 100
        assert f.limit == 25

    def test_filter_by_customer(self):
        cid = uuid.uuid4()
        f = InvoiceFilters(customer_id=cid)
        assert f.customer_id == cid

    def test_filter_by_date_range(self):
        f = InvoiceFilters(date_from=_TODAY, date_to=date(2025, 12, 31))
        assert f.date_from == _TODAY
        assert f.date_to == date(2025, 12, 31)

    def test_overdue_only_flag(self):
        f = InvoiceFilters(overdue_only=True)
        assert f.overdue_only is True


# ── ReorderLinesRequest ────────────────────────────────────────────────────────

class TestReorderLinesRequest:
    def test_accepts_list_of_uuids(self):
        ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        r = ReorderLinesRequest(line_ids=ids)
        assert len(r.line_ids) == 3

    def test_accepts_empty_list(self):
        r = ReorderLinesRequest(line_ids=[])
        assert r.line_ids == []

    def test_line_ids_required(self):
        with pytest.raises(ValidationError):
            ReorderLinesRequest()


# ── PaymentReminderResponse ────────────────────────────────────────────────────

class TestPaymentReminderResponse:
    def test_structure(self):
        r = PaymentReminderResponse(
            invoice_number="FAC-2025-0001",
            customer_name="Empresa S.L.",
            pending_amount=500.50,
            days_overdue=10,
            reminder_text="Estimado cliente, le recordamos...",
        )
        assert r.invoice_number == "FAC-2025-0001"
        assert r.days_overdue == 10
        assert r.pending_amount == 500.50

    def test_not_overdue_uses_zero_days(self):
        r = PaymentReminderResponse(
            invoice_number="FAC-2025-0002",
            customer_name="Cliente",
            pending_amount=1000.00,
            days_overdue=0,
            reminder_text="Su factura vence el 30/06/2025.",
        )
        assert r.days_overdue == 0
