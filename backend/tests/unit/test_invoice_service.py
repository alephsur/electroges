"""
Unit tests for InvoiceService.

All repositories and the session are fully mocked — no database needed.
Covers:
  - Total calculation: subtotal, line discounts, invoice discount, tax
  - Partial payments and full payment triggering PAID status
  - State machine: draft → sent → paid / cancelled / rectification
  - create_invoice (404 for missing customer, number generation)
  - get_invoice / update_invoice
  - send_invoice (draft guard, empty-lines guard)
  - cancel_invoice (SENT/PAID guard, certification revert)
  - create_rectification (copies lines negated, marks original cancelled)
  - register_payment (SENT guard, amount > pending guard, auto-paid)
  - delete_payment (reverts PAID → SENT)
  - add_line / update_line / delete_line (draft guards, 404s)
  - generate_pdf (calls render_invoice_pdf_html + weasyprint)
  - get_payment_reminder (SENT guard, overdue/not-overdue text)
  - _get_effective_status / _get_days_overdue helpers
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import NamedTuple
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from fastapi import HTTPException

from app.models.invoice import Invoice, InvoiceStatus, InvoiceLine, Payment
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceFilters,
    InvoiceFromWorkOrderRequest,
    InvoiceLineCreate,
    InvoiceLineUpdate,
    InvoiceUpdate,
    PaymentCreate,
    RectificationRequest,
    ReorderLinesRequest,
)
from app.services.invoice import InvoiceService

TENANT_ID = uuid.uuid4()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return date.today()


# ── Factories ──────────────────────────────────────────────────────────────────

def make_line(**kwargs) -> MagicMock:
    """Factory for InvoiceLine mocks."""
    ln = MagicMock(spec=InvoiceLine)
    ln.id = uuid.uuid4()
    ln.invoice_id = uuid.uuid4()
    ln.origin_type = MagicMock()
    ln.origin_type.value = "manual"
    ln.origin_id = None
    ln.sort_order = 0
    ln.description = "Línea de prueba"
    ln.quantity = Decimal("1")
    ln.unit = None
    ln.unit_price = Decimal("100.00")
    ln.line_discount_pct = Decimal("0.00")
    ln.created_at = _now()
    ln.updated_at = _now()
    for k, v in kwargs.items():
        setattr(ln, k, v)
    return ln


def make_payment(**kwargs) -> MagicMock:
    """Factory for Payment mocks."""
    p = MagicMock(spec=Payment)
    p.id = uuid.uuid4()
    p.invoice_id = uuid.uuid4()
    p.amount = Decimal("100.00")
    p.payment_date = _today()
    p.method = "transfer"  # plain string — Pydantic rejects MagicMock for str fields
    p.reference = None
    p.notes = None
    p.created_at = _now()
    for k, v in kwargs.items():
        setattr(p, k, v)
    return p


def make_customer(**kwargs) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.name = "Cliente Prueba S.L."
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


def make_company(**kwargs) -> MagicMock:
    co = MagicMock()
    co.default_payment_days = 30
    co.default_tax_rate = Decimal("21.00")
    co.company_name = "ElectroGes S.L."
    co.bank_account = "ES00 0000 0000 0000 0000 0000"
    co.phone = "600 000 000"
    co.email = "info@electroges.com"
    for k, v in kwargs.items():
        setattr(co, k, v)
    return co


def make_invoice(**kwargs) -> MagicMock:
    """Factory for Invoice mocks with sensible defaults."""
    inv = MagicMock(spec=Invoice)
    inv.id = uuid.uuid4()
    inv.tenant_id = TENANT_ID
    inv.invoice_number = "FAC-2025-0001"
    inv.is_rectification = False
    inv.rectifies_invoice_id = None
    inv.customer_id = uuid.uuid4()
    inv.customer = make_customer()
    inv.work_order_id = None
    inv.work_order = None
    inv.status = InvoiceStatus.DRAFT
    inv.issue_date = _today()
    inv.due_date = _today() + timedelta(days=30)
    inv.tax_rate = Decimal("21.00")
    inv.discount_pct = Decimal("0.00")
    inv.notes = None
    inv.client_notes = None
    inv.pdf_path = None
    inv.lines = []
    inv.payments = []
    inv.created_at = _now()
    inv.updated_at = _now()
    for k, v in kwargs.items():
        setattr(inv, k, v)
    return inv


def make_work_order(**kwargs) -> MagicMock:
    wo = MagicMock()
    wo.id = uuid.uuid4()
    wo.customer_id = uuid.uuid4()
    wo.work_order_number = "OBR-2025-0001"
    for k, v in kwargs.items():
        setattr(wo, k, v)
    return wo


def make_task(**kwargs) -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.work_order_id = uuid.uuid4()
    t.name = "Tarea de prueba"
    t.status = MagicMock()
    t.status.value = "completed"
    t.origin_budget_line_id = None
    t.unit_price = Decimal("300.00")
    for k, v in kwargs.items():
        setattr(t, k, v)
    return t


def make_certification(**kwargs) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.work_order_id = uuid.uuid4()
    c.certification_number = "CERT-2025-0001"
    c.status = MagicMock()
    c.status.value = "issued"
    c.invoice_id = None
    c.items = []
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    return session


class _Mocks(NamedTuple):
    svc: InvoiceService
    repo: AsyncMock
    line_repo: AsyncMock
    payment_repo: AsyncMock
    company_repo: AsyncMock
    customer_repo: AsyncMock
    work_order_repo: AsyncMock
    cert_repo: AsyncMock
    task_repo: AsyncMock
    budget_line_repo: AsyncMock
    session: AsyncMock


@pytest.fixture
def mocks(mock_session) -> _Mocks:
    """
    Patches all repositories injected by InvoiceService.__init__.
    Returns a typed NamedTuple so tests can reference repos by name.
    """
    repo = AsyncMock()
    line_repo = AsyncMock()
    payment_repo = AsyncMock()
    company_repo = AsyncMock()
    customer_repo = AsyncMock()
    work_order_repo = AsyncMock()
    cert_repo = AsyncMock()
    task_repo = AsyncMock()
    budget_line_repo = AsyncMock()

    with (
        patch("app.services.invoice.InvoiceRepository", return_value=repo),
        patch("app.services.invoice.InvoiceLineRepository", return_value=line_repo),
        patch("app.services.invoice.PaymentRepository", return_value=payment_repo),
        patch("app.services.invoice.CompanySettingsRepository", return_value=company_repo),
        patch("app.services.invoice.CustomerRepository", return_value=customer_repo),
        patch("app.services.invoice.WorkOrderRepository", return_value=work_order_repo),
        patch("app.services.invoice.CertificationRepository", return_value=cert_repo),
        patch("app.services.invoice.TaskRepository", return_value=task_repo),
        patch("app.services.invoice.BudgetLineRepository", return_value=budget_line_repo),
    ):
        svc = InvoiceService(mock_session, TENANT_ID)
        yield _Mocks(
            svc=svc,
            repo=repo,
            line_repo=line_repo,
            payment_repo=payment_repo,
            company_repo=company_repo,
            customer_repo=customer_repo,
            work_order_repo=work_order_repo,
            cert_repo=cert_repo,
            task_repo=task_repo,
            budget_line_repo=budget_line_repo,
            session=mock_session,
        )


# ── _calculate_totals (private helper tested via public interface) ─────────────

class TestCalculateTotals:
    """
    Tests for InvoiceService._calculate_totals called directly as it is the
    core arithmetic engine of the module.
    """

    def _svc(self) -> InvoiceService:
        """Minimal service instance without patching repos (not needed here)."""
        session = AsyncMock()
        with (
            patch("app.services.invoice.InvoiceRepository"),
            patch("app.services.invoice.InvoiceLineRepository"),
            patch("app.services.invoice.PaymentRepository"),
            patch("app.services.invoice.CompanySettingsRepository"),
            patch("app.services.invoice.CustomerRepository"),
            patch("app.services.invoice.WorkOrderRepository"),
            patch("app.services.invoice.CertificationRepository"),
            patch("app.services.invoice.TaskRepository"),
            patch("app.services.invoice.BudgetLineRepository"),
        ):
            return InvoiceService(session, TENANT_ID)

    def test_no_lines_returns_zero_totals(self):
        svc = self._svc()
        inv = make_invoice(lines=[], payments=[], tax_rate=Decimal("21"), discount_pct=Decimal("0"))
        t = svc._calculate_totals(inv)
        assert t.subtotal_before_discount == Decimal("0.00")
        assert t.total == Decimal("0.00")
        assert t.is_fully_paid is True  # 0 >= 0

    def test_single_line_no_discounts(self):
        svc = self._svc()
        ln = make_line(quantity=Decimal("2"), unit_price=Decimal("100"), line_discount_pct=Decimal("0"))
        inv = make_invoice(lines=[ln], payments=[], tax_rate=Decimal("21"), discount_pct=Decimal("0"))
        t = svc._calculate_totals(inv)
        # 2 × 100 = 200 subtotal; 200 × 1.21 = 242
        assert t.subtotal_before_discount == Decimal("200.00")
        assert t.taxable_base == Decimal("200.00")
        assert t.tax_amount == Decimal("42.00")
        assert t.total == Decimal("242.00")
        assert t.pending_amount == Decimal("242.00")
        assert t.is_fully_paid is False

    def test_line_discount_applied_before_invoice_discount(self):
        svc = self._svc()
        # qty=10, price=100, line_discount=10% → line subtotal = 900
        ln = make_line(quantity=Decimal("10"), unit_price=Decimal("100"), line_discount_pct=Decimal("10"))
        # invoice discount=5% → taxable = 900 * 0.95 = 855
        # tax 21% → 855 * 1.21 = 1034.55
        inv = make_invoice(lines=[ln], payments=[], tax_rate=Decimal("21"), discount_pct=Decimal("5"))
        t = svc._calculate_totals(inv)
        assert t.subtotal_before_discount == Decimal("900.00")
        assert t.discount_amount == Decimal("45.00")
        assert t.taxable_base == Decimal("855.00")
        assert t.tax_amount == Decimal("179.55")
        assert t.total == Decimal("1034.55")

    def test_multiple_lines_summed(self):
        svc = self._svc()
        l1 = make_line(quantity=Decimal("1"), unit_price=Decimal("500"), line_discount_pct=Decimal("0"))
        l2 = make_line(quantity=Decimal("3"), unit_price=Decimal("100"), line_discount_pct=Decimal("0"))
        inv = make_invoice(lines=[l1, l2], payments=[], tax_rate=Decimal("21"), discount_pct=Decimal("0"))
        t = svc._calculate_totals(inv)
        # 500 + 300 = 800 → 800 * 1.21 = 968
        assert t.subtotal_before_discount == Decimal("800.00")
        assert t.total == Decimal("968.00")

    def test_partial_payment_reduces_pending(self):
        svc = self._svc()
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("1000"), line_discount_pct=Decimal("0"))
        p = make_payment(amount=Decimal("600.00"))
        inv = make_invoice(lines=[ln], payments=[p], tax_rate=Decimal("21"), discount_pct=Decimal("0"))
        t = svc._calculate_totals(inv)
        # total = 1210, paid = 600, pending = 610
        assert t.total == Decimal("1210.00")
        assert t.total_paid == Decimal("600.00")
        assert t.pending_amount == Decimal("610.00")
        assert t.is_fully_paid is False

    def test_full_payment_marks_fully_paid(self):
        svc = self._svc()
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("1000"), line_discount_pct=Decimal("0"))
        p = make_payment(amount=Decimal("1210.00"))
        inv = make_invoice(lines=[ln], payments=[p], tax_rate=Decimal("21"), discount_pct=Decimal("0"))
        t = svc._calculate_totals(inv)
        assert t.total_paid == Decimal("1210.00")
        assert t.pending_amount == Decimal("0.00")
        assert t.is_fully_paid is True

    def test_overpayment_pending_is_clamped_to_zero(self):
        """pending_amount must never be negative."""
        svc = self._svc()
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("100"), line_discount_pct=Decimal("0"))
        p1 = make_payment(amount=Decimal("60.50"))
        p2 = make_payment(amount=Decimal("60.50"))
        inv = make_invoice(lines=[ln], payments=[p1, p2], tax_rate=Decimal("0"), discount_pct=Decimal("0"))
        t = svc._calculate_totals(inv)
        # total = 100, paid = 121 → pending = max(0, -21) = 0
        assert t.pending_amount == Decimal("0.00")

    def test_100_percent_discount_total_is_zero(self):
        svc = self._svc()
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("500"), line_discount_pct=Decimal("0"))
        inv = make_invoice(lines=[ln], payments=[], tax_rate=Decimal("21"), discount_pct=Decimal("100"))
        t = svc._calculate_totals(inv)
        assert t.taxable_base == Decimal("0.00")
        assert t.total == Decimal("0.00")

    def test_zero_tax_rate(self):
        svc = self._svc()
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("500"), line_discount_pct=Decimal("0"))
        inv = make_invoice(lines=[ln], payments=[], tax_rate=Decimal("0"), discount_pct=Decimal("0"))
        t = svc._calculate_totals(inv)
        assert t.tax_amount == Decimal("0.00")
        assert t.total == Decimal("500.00")


# ── _get_effective_status ──────────────────────────────────────────────────────

class TestGetEffectiveStatus:
    def _svc(self) -> InvoiceService:
        session = AsyncMock()
        with (
            patch("app.services.invoice.InvoiceRepository"),
            patch("app.services.invoice.InvoiceLineRepository"),
            patch("app.services.invoice.PaymentRepository"),
            patch("app.services.invoice.CompanySettingsRepository"),
            patch("app.services.invoice.CustomerRepository"),
            patch("app.services.invoice.WorkOrderRepository"),
            patch("app.services.invoice.CertificationRepository"),
            patch("app.services.invoice.TaskRepository"),
            patch("app.services.invoice.BudgetLineRepository"),
        ):
            return InvoiceService(session, TENANT_ID)

    def test_draft_returns_draft(self):
        svc = self._svc()
        inv = make_invoice(status=InvoiceStatus.DRAFT, payments=[], lines=[])
        assert svc._get_effective_status(inv) == "draft"

    def test_paid_returns_paid(self):
        svc = self._svc()
        inv = make_invoice(status=InvoiceStatus.PAID, payments=[], lines=[])
        assert svc._get_effective_status(inv) == "paid"

    def test_cancelled_returns_cancelled(self):
        svc = self._svc()
        inv = make_invoice(status=InvoiceStatus.CANCELLED, payments=[], lines=[])
        assert svc._get_effective_status(inv) == "cancelled"

    def test_sent_with_no_payment_and_not_overdue_returns_sent(self):
        svc = self._svc()
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            payments=[],
            lines=[],
            due_date=_today() + timedelta(days=10),
        )
        assert svc._get_effective_status(inv) == "sent"

    def test_sent_with_partial_payment_returns_partially_paid(self):
        svc = self._svc()
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("1000"), line_discount_pct=Decimal("0"))
        p = make_payment(amount=Decimal("500"))
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            lines=[ln],
            payments=[p],
            tax_rate=Decimal("21"),
            discount_pct=Decimal("0"),
            due_date=_today() + timedelta(days=10),
        )
        assert svc._get_effective_status(inv) == "partially_paid"

    def test_sent_overdue_with_no_payment_returns_overdue(self):
        svc = self._svc()
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            payments=[],
            lines=[],
            due_date=_today() - timedelta(days=5),
        )
        assert svc._get_effective_status(inv) == "overdue"


# ── _get_days_overdue ──────────────────────────────────────────────────────────

class TestGetDaysOverdue:
    def _svc(self) -> InvoiceService:
        session = AsyncMock()
        with (
            patch("app.services.invoice.InvoiceRepository"),
            patch("app.services.invoice.InvoiceLineRepository"),
            patch("app.services.invoice.PaymentRepository"),
            patch("app.services.invoice.CompanySettingsRepository"),
            patch("app.services.invoice.CustomerRepository"),
            patch("app.services.invoice.WorkOrderRepository"),
            patch("app.services.invoice.CertificationRepository"),
            patch("app.services.invoice.TaskRepository"),
            patch("app.services.invoice.BudgetLineRepository"),
        ):
            return InvoiceService(session, TENANT_ID)

    def test_draft_returns_zero(self):
        svc = self._svc()
        inv = make_invoice(status=InvoiceStatus.DRAFT, due_date=_today() - timedelta(days=10))
        assert svc._get_days_overdue(inv) == 0

    def test_paid_returns_zero(self):
        svc = self._svc()
        inv = make_invoice(status=InvoiceStatus.PAID, due_date=_today() - timedelta(days=10))
        assert svc._get_days_overdue(inv) == 0

    def test_sent_not_overdue_returns_zero(self):
        svc = self._svc()
        inv = make_invoice(status=InvoiceStatus.SENT, due_date=_today() + timedelta(days=1))
        assert svc._get_days_overdue(inv) == 0

    def test_sent_overdue_returns_positive_days(self):
        svc = self._svc()
        overdue_days = 7
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            due_date=_today() - timedelta(days=overdue_days),
        )
        assert svc._get_days_overdue(inv) == overdue_days


# ── get_invoice ────────────────────────────────────────────────────────────────

class TestGetInvoice:
    async def test_returns_response_when_found(self, mocks: _Mocks):
        inv = make_invoice(lines=[], payments=[])
        mocks.repo.get_with_full_detail.return_value = inv
        result = await mocks.svc.get_invoice(inv.id)
        mocks.repo.get_with_full_detail.assert_called_once_with(inv.id)
        assert result.invoice_number == inv.invoice_number

    async def test_raises_404_when_not_found(self, mocks: _Mocks):
        mocks.repo.get_with_full_detail.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.get_invoice(uuid.uuid4())
        assert exc_info.value.status_code == 404


# ── create_invoice ─────────────────────────────────────────────────────────────

class TestCreateInvoice:
    async def test_raises_404_when_customer_not_found(self, mocks: _Mocks):
        mocks.customer_repo.get_by_id.return_value = None
        mocks.company_repo.get.return_value = make_company()
        mocks.repo.get_next_invoice_number.return_value = "FAC-2025-0001"

        data = InvoiceCreate(customer_id=uuid.uuid4())
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_invoice(data)
        assert exc_info.value.status_code == 404

    async def test_creates_invoice_with_generated_number(self, mocks: _Mocks):
        customer = make_customer()
        company = make_company()
        new_inv = make_invoice(invoice_number="FAC-2025-0042", lines=[], payments=[])

        mocks.customer_repo.get_by_id.return_value = customer
        mocks.company_repo.get.return_value = company
        mocks.repo.get_next_invoice_number.return_value = "FAC-2025-0042"
        mocks.repo.create.return_value = new_inv
        mocks.repo.get_with_full_detail.return_value = new_inv

        data = InvoiceCreate(customer_id=customer.id)
        result = await mocks.svc.create_invoice(data)

        mocks.repo.get_next_invoice_number.assert_called_once()
        mocks.repo.create.assert_called_once()
        assert result.invoice_number == "FAC-2025-0042"

    async def test_due_date_uses_company_payment_days_when_not_provided(self, mocks: _Mocks):
        customer = make_customer()
        company = make_company(default_payment_days=45)
        created_inv = make_invoice(lines=[], payments=[])

        mocks.customer_repo.get_by_id.return_value = customer
        mocks.company_repo.get.return_value = company
        mocks.repo.get_next_invoice_number.return_value = "FAC-2025-0001"
        mocks.repo.create.return_value = created_inv
        mocks.repo.get_with_full_detail.return_value = created_inv

        data = InvoiceCreate(customer_id=customer.id)
        await mocks.svc.create_invoice(data)

        create_call_args = mocks.repo.create.call_args[0][0]
        expected_due = _today() + timedelta(days=45)
        assert create_call_args.due_date == expected_due

    async def test_creates_lines_for_each_line_in_payload(self, mocks: _Mocks):
        customer = make_customer()
        company = make_company()
        created_inv = make_invoice(lines=[], payments=[])

        mocks.customer_repo.get_by_id.return_value = customer
        mocks.company_repo.get.return_value = company
        mocks.repo.get_next_invoice_number.return_value = "FAC-2025-0001"
        mocks.repo.create.return_value = created_inv
        mocks.repo.get_with_full_detail.return_value = created_inv
        mocks.session.flush = AsyncMock()

        data = InvoiceCreate(
            customer_id=customer.id,
            lines=[
                InvoiceLineCreate(description="Linea 1", quantity=Decimal("1"), unit_price=Decimal("100")),
                InvoiceLineCreate(description="Linea 2", quantity=Decimal("2"), unit_price=Decimal("50")),
            ],
        )
        await mocks.svc.create_invoice(data)
        # session.add called twice (once per line)
        assert mocks.session.add.call_count == 2


# ── update_invoice ─────────────────────────────────────────────────────────────

class TestUpdateInvoice:
    async def test_raises_404_when_not_found(self, mocks: _Mocks):
        mocks.repo.get_by_id.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_invoice(uuid.uuid4(), InvoiceUpdate(notes="X"))
        assert exc_info.value.status_code == 404

    async def test_raises_400_when_not_draft(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.SENT)
        mocks.repo.get_by_id.return_value = inv

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_invoice(inv.id, InvoiceUpdate(notes="X"))
        assert exc_info.value.status_code == 400

    async def test_updates_draft_invoice(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.DRAFT, lines=[], payments=[])
        mocks.repo.get_by_id.return_value = inv
        mocks.repo.get_with_full_detail.return_value = inv

        data = InvoiceUpdate(notes="Nota actualizada")
        await mocks.svc.update_invoice(inv.id, data)
        mocks.repo.update.assert_called_once_with(inv, {"notes": "Nota actualizada"})
        mocks.session.commit.assert_called_once()


# ── send_invoice ───────────────────────────────────────────────────────────────

class TestSendInvoice:
    async def test_raises_404_when_not_found(self, mocks: _Mocks):
        mocks.repo.get_with_full_detail.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.send_invoice(uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_raises_400_when_not_draft(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.SENT, lines=[make_line()])
        mocks.repo.get_with_full_detail.return_value = inv
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.send_invoice(inv.id)
        assert exc_info.value.status_code == 400

    async def test_raises_400_when_no_lines(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.DRAFT, lines=[])
        mocks.repo.get_with_full_detail.return_value = inv
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.send_invoice(inv.id)
        assert exc_info.value.status_code == 400

    async def test_sends_draft_invoice_with_lines(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.DRAFT, lines=[make_line()], payments=[])
        mocks.repo.get_with_full_detail.return_value = inv
        mocks.repo.get_with_full_detail.side_effect = [inv, inv]
        mocks.repo.get_with_full_detail.return_value = inv

        await mocks.svc.send_invoice(inv.id)
        mocks.repo.update.assert_called_once_with(inv, {"status": InvoiceStatus.SENT})
        mocks.session.commit.assert_called_once()


# ── cancel_invoice ─────────────────────────────────────────────────────────────

class TestCancelInvoice:
    async def test_raises_404_when_not_found(self, mocks: _Mocks):
        mocks.repo.get_with_full_detail.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.cancel_invoice(uuid.uuid4(), "motivo")
        assert exc_info.value.status_code == 404

    async def test_raises_400_when_sent(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.SENT, lines=[], payments=[])
        mocks.repo.get_with_full_detail.return_value = inv
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.cancel_invoice(inv.id, "motivo")
        assert exc_info.value.status_code == 400

    async def test_raises_400_when_paid(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.PAID, lines=[], payments=[])
        mocks.repo.get_with_full_detail.return_value = inv
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.cancel_invoice(inv.id, "motivo")
        assert exc_info.value.status_code == 400

    async def test_cancels_draft_invoice(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.DRAFT, lines=[], payments=[], notes=None)
        mocks.repo.get_with_full_detail.return_value = inv

        await mocks.svc.cancel_invoice(inv.id, "prueba de cancelación")

        update_call = mocks.repo.update.call_args[0]
        assert update_call[1]["status"] == InvoiceStatus.CANCELLED
        assert "Cancelada" in update_call[1]["notes"]
        assert "prueba de cancelación" in update_call[1]["notes"]
        mocks.session.commit.assert_called_once()

    async def test_cancel_reverts_certifications(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.DRAFT, lines=[], payments=[])
        mocks.repo.get_with_full_detail.return_value = inv

        await mocks.svc.cancel_invoice(inv.id, "error")

        # session.execute must have been called (for the certification revert UPDATE)
        mocks.session.execute.assert_called()


# ── create_rectification ───────────────────────────────────────────────────────

class TestCreateRectification:
    async def test_raises_404_when_not_found(self, mocks: _Mocks):
        mocks.repo.get_with_full_detail.return_value = None
        req = RectificationRequest(reason="Error de precio")
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_rectification(uuid.uuid4(), req)
        assert exc_info.value.status_code == 404

    async def test_raises_400_when_draft(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.DRAFT, lines=[], payments=[])
        mocks.repo.get_with_full_detail.return_value = inv
        req = RectificationRequest(reason="Error de precio")
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_rectification(inv.id, req)
        assert exc_info.value.status_code == 400

    async def test_raises_400_when_cancelled(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.CANCELLED, lines=[], payments=[])
        mocks.repo.get_with_full_detail.return_value = inv
        req = RectificationRequest(reason="Error de precio")
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_rectification(inv.id, req)
        assert exc_info.value.status_code == 400

    async def test_raises_400_when_original_is_already_rectification(self, mocks: _Mocks):
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            is_rectification=True,
            lines=[],
            payments=[],
        )
        mocks.repo.get_with_full_detail.return_value = inv
        req = RectificationRequest(reason="Error de precio")
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_rectification(inv.id, req)
        assert exc_info.value.status_code == 400

    async def test_creates_rectification_with_negated_lines(self, mocks: _Mocks):
        ln = make_line(unit_price=Decimal("200.00"), quantity=Decimal("1"), line_discount_pct=Decimal("0"))
        original = make_invoice(
            status=InvoiceStatus.SENT,
            is_rectification=False,
            lines=[ln],
            payments=[],
        )
        rect_inv = make_invoice(
            invoice_number="FAC-R-2025-0001",
            is_rectification=True,
            rectifies_invoice_id=original.id,
            lines=[],
            payments=[],
        )
        mocks.repo.get_with_full_detail.side_effect = [original, rect_inv]
        mocks.repo.get_next_invoice_number.return_value = "FAC-R-2025-0001"
        mocks.repo.create.return_value = rect_inv
        mocks.company_repo.get.return_value = make_company()

        req = RectificationRequest(reason="Precio incorrecto")
        await mocks.svc.create_rectification(original.id, req)

        # session.add called once for the negated line
        assert mocks.session.add.call_count == 1
        added_line = mocks.session.add.call_args[0][0]
        assert added_line.unit_price == Decimal("-200.00")
        assert added_line.description.startswith("[RECTIFICACIÓN]")

    async def test_original_invoice_marked_cancelled(self, mocks: _Mocks):
        ln = make_line(unit_price=Decimal("100.00"), quantity=Decimal("1"), line_discount_pct=Decimal("0"))
        original = make_invoice(status=InvoiceStatus.PAID, is_rectification=False, lines=[ln], payments=[])
        rect_inv = make_invoice(is_rectification=True, lines=[], payments=[])

        mocks.repo.get_with_full_detail.side_effect = [original, rect_inv]
        mocks.repo.get_next_invoice_number.return_value = "FAC-R-2025-0001"
        mocks.repo.create.return_value = rect_inv
        mocks.company_repo.get.return_value = make_company()

        await mocks.svc.create_rectification(original.id, RectificationRequest(reason="Duplicada"))

        mocks.repo.update.assert_called_once_with(original, {"status": InvoiceStatus.CANCELLED})

    async def test_rectification_number_uses_r_prefix(self, mocks: _Mocks):
        original = make_invoice(status=InvoiceStatus.SENT, is_rectification=False, lines=[], payments=[])
        rect_inv = make_invoice(is_rectification=True, lines=[], payments=[])

        mocks.repo.get_with_full_detail.side_effect = [original, rect_inv]
        mocks.repo.get_next_invoice_number.return_value = "FAC-R-2025-0001"
        mocks.repo.create.return_value = rect_inv
        mocks.company_repo.get.return_value = make_company()

        await mocks.svc.create_rectification(original.id, RectificationRequest(reason="Correccion"))

        mocks.repo.get_next_invoice_number.assert_called_once_with(is_rectification=True)


# ── register_payment ───────────────────────────────────────────────────────────

class TestRegisterPayment:
    async def test_raises_404_when_invoice_not_found(self, mocks: _Mocks):
        mocks.repo.get_with_full_detail.return_value = None
        data = PaymentCreate(amount=Decimal("100"), payment_date=_today(), method="transfer")
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.register_payment(uuid.uuid4(), data)
        assert exc_info.value.status_code == 404

    async def test_raises_400_when_invoice_not_sent(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.DRAFT, lines=[], payments=[])
        mocks.repo.get_with_full_detail.return_value = inv
        data = PaymentCreate(amount=Decimal("100"), payment_date=_today(), method="cash")
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.register_payment(inv.id, data)
        assert exc_info.value.status_code == 400

    async def test_raises_400_when_amount_exceeds_pending(self, mocks: _Mocks):
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("100"), line_discount_pct=Decimal("0"))
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            lines=[ln],
            payments=[],
            tax_rate=Decimal("0"),
            discount_pct=Decimal("0"),
        )
        mocks.repo.get_with_full_detail.return_value = inv
        # pending = 100, try to pay 200
        data = PaymentCreate(amount=Decimal("200"), payment_date=_today(), method="transfer")
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.register_payment(inv.id, data)
        assert exc_info.value.status_code == 400

    async def test_partial_payment_does_not_change_status(self, mocks: _Mocks):
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("1000"), line_discount_pct=Decimal("0"))
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            lines=[ln],
            payments=[],
            tax_rate=Decimal("0"),
            discount_pct=Decimal("0"),
        )
        mocks.repo.get_with_full_detail.return_value = inv

        data = PaymentCreate(amount=Decimal("500"), payment_date=_today(), method="transfer")
        await mocks.svc.register_payment(inv.id, data)

        # repo.update should NOT have been called (status stays SENT)
        mocks.repo.update.assert_not_called()
        mocks.session.add.assert_called_once()

    async def test_full_payment_transitions_to_paid(self, mocks: _Mocks):
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("1000"), line_discount_pct=Decimal("0"))
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            lines=[ln],
            payments=[],
            tax_rate=Decimal("0"),
            discount_pct=Decimal("0"),
        )
        mocks.repo.get_with_full_detail.return_value = inv

        data = PaymentCreate(amount=Decimal("1000"), payment_date=_today(), method="transfer")
        await mocks.svc.register_payment(inv.id, data)

        mocks.repo.update.assert_called_once_with(inv, {"status": InvoiceStatus.PAID})

    async def test_payment_completes_via_accumulated_payments(self, mocks: _Mocks):
        """Second payment that brings total_paid >= total should also trigger PAID."""
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("1000"), line_discount_pct=Decimal("0"))
        existing_payment = make_payment(amount=Decimal("600"))
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            lines=[ln],
            payments=[existing_payment],
            tax_rate=Decimal("0"),
            discount_pct=Decimal("0"),
        )
        mocks.repo.get_with_full_detail.return_value = inv

        # Second payment of 400 → total paid = 1000
        data = PaymentCreate(amount=Decimal("400"), payment_date=_today(), method="cash")
        await mocks.svc.register_payment(inv.id, data)

        mocks.repo.update.assert_called_once_with(inv, {"status": InvoiceStatus.PAID})


# ── delete_payment ─────────────────────────────────────────────────────────────

class TestDeletePayment:
    async def test_raises_404_when_payment_not_found(self, mocks: _Mocks):
        mocks.payment_repo.get_by_id.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_payment(uuid.uuid4(), uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_raises_404_when_payment_belongs_to_different_invoice(self, mocks: _Mocks):
        payment = make_payment(invoice_id=uuid.uuid4())  # different invoice_id
        mocks.payment_repo.get_by_id.return_value = payment
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_payment(uuid.uuid4(), payment.id)
        assert exc_info.value.status_code == 404

    async def test_raises_404_when_invoice_not_found_after_payment(self, mocks: _Mocks):
        invoice_id = uuid.uuid4()
        payment = make_payment(invoice_id=invoice_id)
        mocks.payment_repo.get_by_id.return_value = payment
        mocks.repo.get_with_full_detail.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_payment(invoice_id, payment.id)
        assert exc_info.value.status_code == 404

    async def test_deleting_payment_from_paid_invoice_reverts_to_sent(self, mocks: _Mocks):
        invoice_id = uuid.uuid4()
        payment = make_payment(invoice_id=invoice_id)
        inv = make_invoice(id=invoice_id, status=InvoiceStatus.PAID, lines=[], payments=[payment])
        mocks.payment_repo.get_by_id.return_value = payment
        mocks.repo.get_with_full_detail.return_value = inv

        await mocks.svc.delete_payment(invoice_id, payment.id)

        mocks.repo.update.assert_called_once_with(inv, {"status": InvoiceStatus.SENT})
        mocks.payment_repo.delete.assert_called_once_with(payment)

    async def test_deleting_payment_from_sent_invoice_does_not_change_status(self, mocks: _Mocks):
        invoice_id = uuid.uuid4()
        payment = make_payment(invoice_id=invoice_id)
        inv = make_invoice(id=invoice_id, status=InvoiceStatus.SENT, lines=[], payments=[payment])
        mocks.payment_repo.get_by_id.return_value = payment
        mocks.repo.get_with_full_detail.return_value = inv

        await mocks.svc.delete_payment(invoice_id, payment.id)

        mocks.repo.update.assert_not_called()
        mocks.payment_repo.delete.assert_called_once_with(payment)


# ── add_line ───────────────────────────────────────────────────────────────────

class TestAddLine:
    async def test_raises_404_when_invoice_not_found(self, mocks: _Mocks):
        mocks.repo.get_by_id.return_value = None
        data = InvoiceLineCreate(description="Item", quantity=Decimal("1"), unit_price=Decimal("50"))
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.add_line(uuid.uuid4(), data)
        assert exc_info.value.status_code == 404

    async def test_raises_400_when_not_draft(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.SENT)
        mocks.repo.get_by_id.return_value = inv
        data = InvoiceLineCreate(description="Item", quantity=Decimal("1"), unit_price=Decimal("50"))
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.add_line(inv.id, data)
        assert exc_info.value.status_code == 400

    async def test_adds_line_to_draft_invoice(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.DRAFT, lines=[], payments=[])
        mocks.repo.get_by_id.return_value = inv
        mocks.repo.get_with_full_detail.return_value = inv
        mocks.session.flush = AsyncMock()

        data = InvoiceLineCreate(description="Nueva línea", quantity=Decimal("2"), unit_price=Decimal("75"))
        await mocks.svc.add_line(inv.id, data)

        mocks.session.add.assert_called_once()
        mocks.session.commit.assert_called_once()


# ── update_line ────────────────────────────────────────────────────────────────

class TestUpdateLine:
    async def test_raises_404_when_line_not_found(self, mocks: _Mocks):
        mocks.line_repo.get_by_id.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_line(uuid.uuid4(), uuid.uuid4(), InvoiceLineUpdate(description="X"))
        assert exc_info.value.status_code == 404

    async def test_raises_404_when_line_belongs_to_different_invoice(self, mocks: _Mocks):
        line = make_line(invoice_id=uuid.uuid4())
        mocks.line_repo.get_by_id.return_value = line
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_line(uuid.uuid4(), line.id, InvoiceLineUpdate(description="X"))
        assert exc_info.value.status_code == 404

    async def test_raises_400_when_invoice_not_draft(self, mocks: _Mocks):
        invoice_id = uuid.uuid4()
        line = make_line(invoice_id=invoice_id)
        inv = make_invoice(id=invoice_id, status=InvoiceStatus.SENT)
        mocks.line_repo.get_by_id.return_value = line
        mocks.repo.get_by_id.return_value = inv
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_line(invoice_id, line.id, InvoiceLineUpdate(description="X"))
        assert exc_info.value.status_code == 400

    async def test_updates_line_in_draft_invoice(self, mocks: _Mocks):
        invoice_id = uuid.uuid4()
        line = make_line(invoice_id=invoice_id)
        inv = make_invoice(id=invoice_id, status=InvoiceStatus.DRAFT, lines=[line], payments=[])
        mocks.line_repo.get_by_id.return_value = line
        mocks.repo.get_by_id.return_value = inv
        mocks.repo.get_with_full_detail.return_value = inv

        data = InvoiceLineUpdate(description="Descripción actualizada", unit_price=Decimal("200"))
        await mocks.svc.update_line(invoice_id, line.id, data)

        mocks.line_repo.update.assert_called_once_with(
            line, {"description": "Descripción actualizada", "unit_price": Decimal("200")}
        )
        mocks.session.commit.assert_called_once()


# ── delete_line ────────────────────────────────────────────────────────────────

class TestDeleteLine:
    async def test_raises_404_when_line_not_found(self, mocks: _Mocks):
        mocks.line_repo.get_by_id.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_line(uuid.uuid4(), uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_raises_404_when_line_belongs_to_different_invoice(self, mocks: _Mocks):
        line = make_line(invoice_id=uuid.uuid4())
        mocks.line_repo.get_by_id.return_value = line
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_line(uuid.uuid4(), line.id)
        assert exc_info.value.status_code == 404

    async def test_raises_400_when_not_draft(self, mocks: _Mocks):
        invoice_id = uuid.uuid4()
        line = make_line(invoice_id=invoice_id)
        inv = make_invoice(id=invoice_id, status=InvoiceStatus.SENT)
        mocks.line_repo.get_by_id.return_value = line
        mocks.repo.get_by_id.return_value = inv
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.delete_line(invoice_id, line.id)
        assert exc_info.value.status_code == 400

    async def test_deletes_line_from_draft_invoice(self, mocks: _Mocks):
        invoice_id = uuid.uuid4()
        line = make_line(invoice_id=invoice_id)
        inv = make_invoice(id=invoice_id, status=InvoiceStatus.DRAFT, lines=[line], payments=[])
        mocks.line_repo.get_by_id.return_value = line
        mocks.repo.get_by_id.return_value = inv
        mocks.repo.get_with_full_detail.return_value = inv

        await mocks.svc.delete_line(invoice_id, line.id)

        mocks.line_repo.delete.assert_called_once_with(line)
        mocks.session.commit.assert_called_once()


# ── generate_pdf ───────────────────────────────────────────────────────────────

class TestGeneratePdf:
    async def test_raises_404_when_not_found(self, mocks: _Mocks):
        mocks.repo.get_with_full_detail.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.generate_pdf(uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_calls_renderer_and_weasyprint(self, mocks: _Mocks, tmp_path):
        inv = make_invoice(
            lines=[make_line(quantity=Decimal("1"), unit_price=Decimal("100"), line_discount_pct=Decimal("0"))],
            payments=[],
            tax_rate=Decimal("21"),
            discount_pct=Decimal("0"),
        )
        mocks.repo.get_with_full_detail.return_value = inv
        mocks.company_repo.get.return_value = make_company()

        fake_pdf_bytes = b"%PDF-fake"

        with (
            patch("app.services.invoice.render_invoice_pdf_html", return_value="<html></html>") as mock_render,
            patch("weasyprint.HTML") as mock_html_cls,
            patch("app.services.invoice.settings") as mock_settings,
        ):
            mock_settings.UPLOAD_DIR = str(tmp_path)
            mock_html_instance = MagicMock()
            mock_html_cls.return_value = mock_html_instance
            mock_html_instance.write_pdf.return_value = fake_pdf_bytes

            result = await mocks.svc.generate_pdf(inv.id)

        mock_render.assert_called_once()
        mock_html_cls.assert_called_once_with(string="<html></html>")
        mock_html_instance.write_pdf.assert_called_once()
        assert result == fake_pdf_bytes

    async def test_pdf_path_saved_to_invoice(self, mocks: _Mocks, tmp_path):
        inv = make_invoice(
            lines=[make_line(quantity=Decimal("1"), unit_price=Decimal("100"), line_discount_pct=Decimal("0"))],
            payments=[],
            tax_rate=Decimal("21"),
            discount_pct=Decimal("0"),
        )
        mocks.repo.get_with_full_detail.return_value = inv
        mocks.company_repo.get.return_value = make_company()

        with (
            patch("app.services.invoice.render_invoice_pdf_html", return_value="<html></html>"),
            patch("weasyprint.HTML") as mock_html_cls,
            patch("app.services.invoice.settings") as mock_settings,
        ):
            mock_settings.UPLOAD_DIR = str(tmp_path)
            mock_html_instance = MagicMock()
            mock_html_cls.return_value = mock_html_instance
            mock_html_instance.write_pdf.return_value = b"%PDF"

            await mocks.svc.generate_pdf(inv.id)

        update_call = mocks.repo.update.call_args[0]
        assert "pdf_path" in update_call[1]
        assert str(inv.id) in update_call[1]["pdf_path"]


# ── get_payment_reminder ───────────────────────────────────────────────────────

class TestGetPaymentReminder:
    async def test_raises_404_when_not_found(self, mocks: _Mocks):
        mocks.repo.get_with_full_detail.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.get_payment_reminder(uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_raises_400_when_not_sent(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.DRAFT, lines=[], payments=[])
        mocks.repo.get_with_full_detail.return_value = inv
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.get_payment_reminder(inv.id)
        assert exc_info.value.status_code == 400

    async def test_raises_400_when_paid(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.PAID, lines=[], payments=[])
        mocks.repo.get_with_full_detail.return_value = inv
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.get_payment_reminder(inv.id)
        assert exc_info.value.status_code == 400

    async def test_generates_reminder_for_sent_invoice(self, mocks: _Mocks):
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("1000"), line_discount_pct=Decimal("0"))
        customer = make_customer(name="Empresa S.L.")
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            lines=[ln],
            payments=[],
            customer=customer,
            tax_rate=Decimal("0"),
            discount_pct=Decimal("0"),
            due_date=_today() + timedelta(days=5),
        )
        mocks.repo.get_with_full_detail.return_value = inv
        mocks.company_repo.get.return_value = make_company()

        result = await mocks.svc.get_payment_reminder(inv.id)

        assert result.invoice_number == inv.invoice_number
        assert result.customer_name == "Empresa S.L."
        assert result.days_overdue == 0
        assert result.pending_amount == 1000.0
        assert inv.invoice_number in result.reminder_text

    async def test_reminder_text_contains_overdue_message_when_past_due(self, mocks: _Mocks):
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("500"), line_discount_pct=Decimal("0"))
        customer = make_customer(name="Cliente Moroso")
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            lines=[ln],
            payments=[],
            customer=customer,
            tax_rate=Decimal("0"),
            discount_pct=Decimal("0"),
            due_date=_today() - timedelta(days=15),
        )
        mocks.repo.get_with_full_detail.return_value = inv
        mocks.company_repo.get.return_value = make_company()

        result = await mocks.svc.get_payment_reminder(inv.id)

        assert result.days_overdue == 15
        assert "15" in result.reminder_text  # overdue days appear in text

    async def test_reminder_text_contains_vencimiento_when_not_overdue(self, mocks: _Mocks):
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("200"), line_discount_pct=Decimal("0"))
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            lines=[ln],
            payments=[],
            customer=make_customer(),
            tax_rate=Decimal("0"),
            discount_pct=Decimal("0"),
            due_date=_today() + timedelta(days=10),
        )
        mocks.repo.get_with_full_detail.return_value = inv
        mocks.company_repo.get.return_value = make_company()

        result = await mocks.svc.get_payment_reminder(inv.id)

        assert result.days_overdue == 0
        assert "vence el" in result.reminder_text

    async def test_reminder_includes_company_bank_account(self, mocks: _Mocks):
        ln = make_line(quantity=Decimal("1"), unit_price=Decimal("100"), line_discount_pct=Decimal("0"))
        inv = make_invoice(
            status=InvoiceStatus.SENT,
            lines=[ln],
            payments=[],
            customer=make_customer(),
            tax_rate=Decimal("0"),
            discount_pct=Decimal("0"),
            due_date=_today() + timedelta(days=30),
        )
        company = make_company(bank_account="ES12 3456 7890 1234 5678 9012")
        mocks.repo.get_with_full_detail.return_value = inv
        mocks.company_repo.get.return_value = company

        result = await mocks.svc.get_payment_reminder(inv.id)

        assert "ES12 3456 7890 1234 5678 9012" in result.reminder_text


# ── list_invoices ──────────────────────────────────────────────────────────────

class TestListInvoices:
    async def test_returns_list_response(self, mocks: _Mocks):
        inv = make_invoice(lines=[], payments=[])
        mocks.repo.search.return_value = ([inv], 1)

        filters = InvoiceFilters()
        result = await mocks.svc.list_invoices(filters)

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].invoice_number == inv.invoice_number

    async def test_empty_results(self, mocks: _Mocks):
        mocks.repo.search.return_value = ([], 0)
        result = await mocks.svc.list_invoices(InvoiceFilters())
        assert result.total == 0
        assert result.items == []

    async def test_passes_filters_to_repo(self, mocks: _Mocks):
        mocks.repo.search.return_value = ([], 0)
        cid = uuid.uuid4()
        filters = InvoiceFilters(customer_id=cid, status="sent", overdue_only=True, skip=10, limit=20)
        await mocks.svc.list_invoices(filters)

        call_kwargs = mocks.repo.search.call_args
        # verify positional args include customer_id and status
        args = call_kwargs[0]
        assert cid in args
        assert "sent" in args


# ── create_from_work_order ─────────────────────────────────────────────────────

class TestCreateFromWorkOrder:
    async def test_raises_404_when_work_order_not_found(self, mocks: _Mocks):
        mocks.work_order_repo.get_with_full_detail.return_value = None
        req = InvoiceFromWorkOrderRequest(
            work_order_id=uuid.uuid4(),
            task_ids=[uuid.uuid4()],
        )
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_from_work_order(req)
        assert exc_info.value.status_code == 404

    async def test_raises_404_when_certification_not_in_work_order(self, mocks: _Mocks):
        work_order = make_work_order()
        cert = make_certification(work_order_id=uuid.uuid4())  # different work_order_id
        new_inv = make_invoice(lines=[], payments=[])

        mocks.work_order_repo.get_with_full_detail.return_value = work_order
        mocks.company_repo.get.return_value = make_company()
        mocks.repo.get_next_invoice_number.return_value = "FAC-2025-0001"
        mocks.repo.create.return_value = new_inv
        mocks.cert_repo.get_by_id.return_value = cert

        req = InvoiceFromWorkOrderRequest(
            work_order_id=work_order.id,
            certification_ids=[cert.id],
        )
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_from_work_order(req)
        assert exc_info.value.status_code == 404

    async def test_raises_400_when_certification_not_issued(self, mocks: _Mocks):
        work_order = make_work_order()
        cert = make_certification(work_order_id=work_order.id)
        cert.status.value = "draft"  # not "issued"
        new_inv = make_invoice(lines=[], payments=[])

        mocks.work_order_repo.get_with_full_detail.return_value = work_order
        mocks.company_repo.get.return_value = make_company()
        mocks.repo.get_next_invoice_number.return_value = "FAC-2025-0001"
        mocks.repo.create.return_value = new_inv
        mocks.cert_repo.get_by_id.return_value = cert

        req = InvoiceFromWorkOrderRequest(
            work_order_id=work_order.id,
            certification_ids=[cert.id],
        )
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_from_work_order(req)
        assert exc_info.value.status_code == 400

    async def test_raises_400_when_task_not_completed(self, mocks: _Mocks):
        work_order = make_work_order()
        task = make_task(work_order_id=work_order.id)
        task.status.value = "in_progress"  # not completed
        new_inv = make_invoice(lines=[], payments=[])

        mocks.work_order_repo.get_with_full_detail.return_value = work_order
        mocks.company_repo.get.return_value = make_company()
        mocks.repo.get_next_invoice_number.return_value = "FAC-2025-0001"
        mocks.repo.create.return_value = new_inv
        mocks.task_repo.get_by_id.return_value = task

        # session.execute returns an AsyncMock by default — override with a plain
        # MagicMock so that .all() returns a list instead of a coroutine.
        result_mock = MagicMock()
        result_mock.all.return_value = []
        mocks.session.execute.return_value = result_mock

        req = InvoiceFromWorkOrderRequest(
            work_order_id=work_order.id,
            task_ids=[task.id],
        )
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_from_work_order(req)
        assert exc_info.value.status_code == 400

    async def test_raises_400_when_task_already_invoiced(self, mocks: _Mocks):
        work_order = make_work_order()
        task = make_task(work_order_id=work_order.id)
        already_invoiced_task_id = task.id
        new_inv = make_invoice(lines=[], payments=[])

        mocks.work_order_repo.get_with_full_detail.return_value = work_order
        mocks.company_repo.get.return_value = make_company()
        mocks.repo.get_next_invoice_number.return_value = "FAC-2025-0001"
        mocks.repo.create.return_value = new_inv

        # Simulate that _get_invoiced_task_ids returns the task id
        result_mock = MagicMock()
        result_mock.all.return_value = [(already_invoiced_task_id,)]
        mocks.session.execute.return_value = result_mock

        req = InvoiceFromWorkOrderRequest(
            work_order_id=work_order.id,
            task_ids=[task.id],
        )
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.create_from_work_order(req)
        assert exc_info.value.status_code == 400


# ── reorder_lines ──────────────────────────────────────────────────────────────

class TestReorderLines:
    async def test_raises_404_when_invoice_not_found_or_not_draft(self, mocks: _Mocks):
        mocks.repo.get_by_id.return_value = None
        data = ReorderLinesRequest(line_ids=[uuid.uuid4()])
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.reorder_lines(uuid.uuid4(), data)
        assert exc_info.value.status_code == 404

    async def test_raises_404_when_invoice_not_draft(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.SENT)
        mocks.repo.get_by_id.return_value = inv
        data = ReorderLinesRequest(line_ids=[uuid.uuid4()])
        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.reorder_lines(inv.id, data)
        assert exc_info.value.status_code == 404

    async def test_executes_update_for_each_line(self, mocks: _Mocks):
        inv = make_invoice(status=InvoiceStatus.DRAFT, lines=[], payments=[])
        mocks.repo.get_by_id.return_value = inv
        mocks.repo.get_with_full_detail.return_value = inv

        ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        data = ReorderLinesRequest(line_ids=ids)
        await mocks.svc.reorder_lines(inv.id, data)

        # session.execute called once per line_id
        assert mocks.session.execute.call_count == len(ids)
        mocks.session.commit.assert_called_once()
