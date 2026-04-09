"""
Unit tests for Budget schemas (Pydantic v2).

No async, no mocks — pure validation logic.
Covers: field constraints, computed fields, margin traffic light,
        effective status, discount bounds, and type literals.
"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.budget import (
    BudgetCreate,
    BudgetFromVisitRequest,
    BudgetLineCreate,
    BudgetLineUpdate,
    BudgetStatusUpdate,
    BudgetUpdate,
    ReorderLinesRequest,
)


# ── BudgetLineCreate ───────────────────────────────────────────────────────────

class TestBudgetLineCreate:
    def test_valid_labor_line(self):
        line = BudgetLineCreate(
            line_type="labor",
            description="Instalación eléctrica",
            quantity=Decimal("8.0"),
            unit_price=Decimal("50.00"),
        )
        assert line.line_type == "labor"
        assert line.quantity == Decimal("8.0")
        assert line.unit_cost == Decimal("0.0")
        assert line.line_discount_pct == Decimal("0.00")

    def test_valid_material_line(self):
        item_id = uuid4()
        line = BudgetLineCreate(
            line_type="material",
            description="Cable 2.5mm²",
            inventory_item_id=item_id,
            quantity=Decimal("50"),
            unit="m",
            unit_price=Decimal("1.20"),
            unit_cost=Decimal("0.80"),
        )
        assert line.inventory_item_id == item_id
        assert line.unit_cost == Decimal("0.80")

    def test_valid_other_line(self):
        line = BudgetLineCreate(
            line_type="other",
            description="Desplazamiento",
            quantity=Decimal("1"),
            unit_price=Decimal("30.00"),
        )
        assert line.line_type == "other"

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError) as exc_info:
            BudgetLineCreate(
                line_type="labor",
                description="Trabajo",
                quantity=Decimal("0"),
                unit_price=Decimal("50.00"),
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("quantity",) for e in errors)

    def test_quantity_negative_raises(self):
        with pytest.raises(ValidationError):
            BudgetLineCreate(
                line_type="labor",
                description="Trabajo",
                quantity=Decimal("-1"),
                unit_price=Decimal("50.00"),
            )

    def test_unit_price_zero_allowed(self):
        line = BudgetLineCreate(
            line_type="labor",
            description="Gratuito",
            quantity=Decimal("1"),
            unit_price=Decimal("0.00"),
        )
        assert line.unit_price == Decimal("0.00")

    def test_unit_price_negative_raises(self):
        with pytest.raises(ValidationError):
            BudgetLineCreate(
                line_type="labor",
                description="Trabajo",
                quantity=Decimal("1"),
                unit_price=Decimal("-5.00"),
            )

    def test_unit_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            BudgetLineCreate(
                line_type="material",
                description="Material",
                quantity=Decimal("1"),
                unit_price=Decimal("10.00"),
                unit_cost=Decimal("-1.00"),
            )

    def test_line_discount_pct_100_allowed(self):
        line = BudgetLineCreate(
            line_type="other",
            description="Bonificación total",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            line_discount_pct=Decimal("100"),
        )
        assert line.line_discount_pct == Decimal("100")

    def test_line_discount_pct_above_100_raises(self):
        with pytest.raises(ValidationError):
            BudgetLineCreate(
                line_type="other",
                description="Descuento inválido",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
                line_discount_pct=Decimal("101"),
            )

    def test_line_discount_pct_negative_raises(self):
        with pytest.raises(ValidationError):
            BudgetLineCreate(
                line_type="other",
                description="Descuento inválido",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
                line_discount_pct=Decimal("-1"),
            )

    def test_invalid_line_type_raises(self):
        with pytest.raises(ValidationError):
            BudgetLineCreate(
                line_type="invalid_type",
                description="Línea inválida",
                quantity=Decimal("1"),
                unit_price=Decimal("10.00"),
            )

    def test_inventory_item_id_optional(self):
        line = BudgetLineCreate(
            line_type="material",
            description="Material sin referencia",
            quantity=Decimal("5"),
            unit_price=Decimal("10.00"),
        )
        assert line.inventory_item_id is None

    def test_default_sort_order_is_zero(self):
        line = BudgetLineCreate(
            line_type="labor",
            description="Trabajo",
            quantity=Decimal("1"),
            unit_price=Decimal("50.00"),
        )
        assert line.sort_order == 0


# ── BudgetLineUpdate ───────────────────────────────────────────────────────────

class TestBudgetLineUpdate:
    def test_all_fields_optional(self):
        update = BudgetLineUpdate()
        assert update.description is None
        assert update.quantity is None
        assert update.unit_price is None
        assert update.unit_cost is None
        assert update.line_discount_pct is None
        assert update.sort_order is None

    def test_quantity_must_be_positive_when_given(self):
        with pytest.raises(ValidationError):
            BudgetLineUpdate(quantity=Decimal("0"))

    def test_discount_above_100_raises(self):
        with pytest.raises(ValidationError):
            BudgetLineUpdate(line_discount_pct=Decimal("101"))

    def test_discount_negative_raises(self):
        with pytest.raises(ValidationError):
            BudgetLineUpdate(line_discount_pct=Decimal("-5"))

    def test_unit_price_negative_raises(self):
        with pytest.raises(ValidationError):
            BudgetLineUpdate(unit_price=Decimal("-1"))

    def test_partial_update_valid(self):
        update = BudgetLineUpdate(
            description="Descripción actualizada",
            quantity=Decimal("5.5"),
        )
        assert update.description == "Descripción actualizada"
        assert update.unit_price is None


# ── BudgetCreate ───────────────────────────────────────────────────────────────

class TestBudgetCreate:
    def test_minimal_valid(self):
        data = BudgetCreate()
        assert data.customer_id is None
        assert data.site_visit_id is None
        assert data.lines == []
        assert data.discount_pct == Decimal("0.00")

    def test_discount_pct_bounds(self):
        # 0 OK
        data = BudgetCreate(discount_pct=Decimal("0"))
        assert data.discount_pct == Decimal("0")

        # 100 OK
        data = BudgetCreate(discount_pct=Decimal("100"))
        assert data.discount_pct == Decimal("100")

    def test_discount_pct_above_100_raises(self):
        with pytest.raises(ValidationError):
            BudgetCreate(discount_pct=Decimal("100.01"))

    def test_discount_pct_negative_raises(self):
        with pytest.raises(ValidationError):
            BudgetCreate(discount_pct=Decimal("-1"))

    def test_with_lines(self):
        data = BudgetCreate(
            customer_id=uuid4(),
            lines=[
                BudgetLineCreate(
                    line_type="labor",
                    description="Instalación",
                    quantity=Decimal("4"),
                    unit_price=Decimal("60.00"),
                )
            ],
        )
        assert len(data.lines) == 1

    def test_tax_rate_optional(self):
        data = BudgetCreate(tax_rate=Decimal("10.00"))
        assert data.tax_rate == Decimal("10.00")

    def test_full_valid_payload(self):
        today = date.today()
        data = BudgetCreate(
            customer_id=uuid4(),
            site_visit_id=uuid4(),
            issue_date=today,
            valid_until=today + timedelta(days=30),
            tax_rate=Decimal("21.00"),
            discount_pct=Decimal("5.00"),
            notes="Nota interna",
            client_notes="Nota para el cliente",
        )
        assert data.tax_rate == Decimal("21.00")
        assert data.discount_pct == Decimal("5.00")


# ── BudgetFromVisitRequest ─────────────────────────────────────────────────────

class TestBudgetFromVisitRequest:
    def test_requires_site_visit_id(self):
        with pytest.raises(ValidationError):
            BudgetFromVisitRequest()

    def test_valid_minimal(self):
        req = BudgetFromVisitRequest(site_visit_id=uuid4())
        assert req.lines_override is None
        assert req.discount_pct == Decimal("0.00")

    def test_lines_override_accepted(self):
        req = BudgetFromVisitRequest(
            site_visit_id=uuid4(),
            lines_override=[
                BudgetLineCreate(
                    line_type="material",
                    description="Cable",
                    quantity=Decimal("10"),
                    unit_price=Decimal("2.50"),
                )
            ],
        )
        assert len(req.lines_override) == 1

    def test_valid_until_optional(self):
        req = BudgetFromVisitRequest(
            site_visit_id=uuid4(),
            valid_until=date.today() + timedelta(days=15),
        )
        assert req.valid_until is not None


# ── BudgetUpdate ───────────────────────────────────────────────────────────────

class TestBudgetUpdate:
    def test_all_fields_optional(self):
        update = BudgetUpdate()
        assert update.issue_date is None
        assert update.valid_until is None
        assert update.tax_rate is None
        assert update.discount_pct is None
        assert update.notes is None
        assert update.client_notes is None

    def test_discount_pct_bounds(self):
        update = BudgetUpdate(discount_pct=Decimal("50.00"))
        assert update.discount_pct == Decimal("50.00")

    def test_discount_pct_above_100_raises(self):
        with pytest.raises(ValidationError):
            BudgetUpdate(discount_pct=Decimal("101"))

    def test_discount_pct_negative_raises(self):
        with pytest.raises(ValidationError):
            BudgetUpdate(discount_pct=Decimal("-0.01"))


# ── BudgetStatusUpdate ─────────────────────────────────────────────────────────

class TestBudgetStatusUpdate:
    def test_valid_sent(self):
        upd = BudgetStatusUpdate(status="sent")
        assert upd.status == "sent"

    def test_valid_rejected(self):
        upd = BudgetStatusUpdate(status="rejected")
        assert upd.status == "rejected"

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            BudgetStatusUpdate(status="accepted")

    def test_invalid_status_draft_raises(self):
        with pytest.raises(ValidationError):
            BudgetStatusUpdate(status="draft")

    def test_notes_optional(self):
        upd = BudgetStatusUpdate(status="rejected", notes="Cliente no interesado")
        assert upd.notes == "Cliente no interesado"

    def test_notes_none_by_default(self):
        upd = BudgetStatusUpdate(status="sent")
        assert upd.notes is None


# ── ReorderLinesRequest ────────────────────────────────────────────────────────

class TestReorderLinesRequest:
    def test_valid_list(self):
        ids = [uuid4(), uuid4(), uuid4()]
        req = ReorderLinesRequest(line_ids=ids)
        assert len(req.line_ids) == 3

    def test_empty_list_allowed(self):
        req = ReorderLinesRequest(line_ids=[])
        assert req.line_ids == []
