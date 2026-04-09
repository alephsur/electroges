"""
Unit tests for Supplier, SupplierItem and PurchaseOrder schemas (Pydantic v2).

No async, no mocks — pure validation and serialisation logic.
Covers: field constraints, computed fields, model validators, defaults.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.supplier import (
    SupplierCreate,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdate,
)
from app.schemas.supplier_item import (
    SupplierItemCreate,
    SupplierItemResponse,
    SupplierItemUpdate,
)
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderLineCreate,
    PurchaseOrderListResponse,
    PurchaseOrderResponse,
    PurchaseOrderSummary,
    PurchaseOrderUpdate,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── SupplierCreate ─────────────────────────────────────────────────────────────


class TestSupplierCreate:
    def test_minimal_valid(self):
        s = SupplierCreate(name="Proveedor ABC")
        assert s.name == "Proveedor ABC"
        assert s.tax_id is None
        assert s.email is None
        assert s.phone is None
        assert s.address is None
        assert s.contact_person is None
        assert s.payment_terms is None
        assert s.notes is None

    def test_all_fields(self):
        s = SupplierCreate(
            name="Distribuciones García",
            tax_id="B12345678",
            email="info@garcia.es",
            phone="912345678",
            address="Calle Mayor 1, 28001 Madrid",
            contact_person="Carlos García",
            payment_terms="30 días",
            notes="Descuento por volumen 5%",
        )
        assert s.tax_id == "B12345678"
        assert s.email == "info@garcia.es"
        assert s.contact_person == "Carlos García"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            SupplierCreate(name="X", email="not-an-email")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("email",) for e in errors)

    def test_name_required(self):
        with pytest.raises(ValidationError):
            SupplierCreate()

    def test_valid_email_formats(self):
        # Pydantic accepts both standard forms
        s1 = SupplierCreate(name="A", email="user+tag@sub.domain.com")
        assert s1.email == "user+tag@sub.domain.com"


# ── SupplierUpdate ─────────────────────────────────────────────────────────────


class TestSupplierUpdate:
    def test_all_fields_optional(self):
        u = SupplierUpdate()
        assert u.name is None
        assert u.is_active is None

    def test_partial_update(self):
        u = SupplierUpdate(name="Nuevo Nombre", is_active=False)
        assert u.name == "Nuevo Nombre"
        assert u.is_active is False

    def test_invalid_email_on_update_raises(self):
        with pytest.raises(ValidationError):
            SupplierUpdate(email="bad")

    def test_model_dump_exclude_unset(self):
        u = SupplierUpdate(notes="nueva nota")
        d = u.model_dump(exclude_unset=True)
        assert list(d.keys()) == ["notes"]

    def test_activate_supplier(self):
        u = SupplierUpdate(is_active=True)
        assert u.is_active is True


# ── SupplierResponse ───────────────────────────────────────────────────────────


class TestSupplierResponse:
    def _make_data(self, **kwargs) -> dict:
        defaults = dict(
            id=uuid4(),
            name="Proveedor Test",
            tax_id="A87654321",
            email="test@proveedor.com",
            phone="600111222",
            address="Calle Falsa 123",
            contact_person="Pedro",
            payment_terms="60 días",
            notes=None,
            is_active=True,
            created_at=_now(),
            updated_at=_now(),
        )
        defaults.update(kwargs)
        return defaults

    def test_valid_response(self):
        r = SupplierResponse(**self._make_data())
        assert r.is_active is True
        assert isinstance(r.id, type(uuid4()))

    def test_nullable_fields_can_be_none(self):
        r = SupplierResponse(**self._make_data(tax_id=None, email=None, phone=None))
        assert r.tax_id is None
        assert r.email is None

    def test_from_attributes_enabled(self):
        from unittest.mock import MagicMock

        m = MagicMock()
        m.id = uuid4()
        m.name = "Mock Supplier"
        m.tax_id = None
        m.email = None
        m.phone = None
        m.address = None
        m.contact_person = None
        m.payment_terms = None
        m.notes = None
        m.is_active = True
        m.created_at = _now()
        m.updated_at = _now()

        r = SupplierResponse.model_validate(m)
        assert r.name == "Mock Supplier"


class TestSupplierListResponse:
    def _make_supplier_response(self, **kwargs) -> SupplierResponse:
        defaults = dict(
            id=uuid4(),
            name="S",
            tax_id=None,
            email=None,
            phone=None,
            address=None,
            contact_person=None,
            payment_terms=None,
            notes=None,
            is_active=True,
            created_at=_now(),
            updated_at=_now(),
        )
        defaults.update(kwargs)
        return SupplierResponse(**defaults)

    def test_valid_list_response(self):
        r = SupplierListResponse(
            items=[self._make_supplier_response(), self._make_supplier_response()],
            total=2,
            skip=0,
            limit=100,
        )
        assert r.total == 2
        assert len(r.items) == 2

    def test_empty_list(self):
        r = SupplierListResponse(items=[], total=0, skip=0, limit=100)
        assert r.total == 0

    def test_pagination_fields(self):
        r = SupplierListResponse(items=[], total=50, skip=20, limit=10)
        assert r.skip == 20
        assert r.limit == 10


# ── SupplierItemCreate ─────────────────────────────────────────────────────────


class TestSupplierItemCreate:
    def test_valid_minimal(self):
        si = SupplierItemCreate(
            supplier_id=uuid4(),
            inventory_item_id=uuid4(),
            unit_cost=Decimal("1.50"),
        )
        assert si.is_preferred is False
        assert si.supplier_ref is None
        assert si.lead_time_days is None

    def test_full_fields(self):
        si = SupplierItemCreate(
            supplier_id=uuid4(),
            inventory_item_id=uuid4(),
            unit_cost=Decimal("2.99"),
            supplier_ref="REF-001",
            lead_time_days=5,
            is_preferred=True,
        )
        assert si.supplier_ref == "REF-001"
        assert si.lead_time_days == 5
        assert si.is_preferred is True

    def test_unit_cost_must_be_positive(self):
        with pytest.raises(ValidationError) as exc_info:
            SupplierItemCreate(
                supplier_id=uuid4(),
                inventory_item_id=uuid4(),
                unit_cost=Decimal("0"),
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("unit_cost",) for e in errors)

    def test_unit_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            SupplierItemCreate(
                supplier_id=uuid4(),
                inventory_item_id=uuid4(),
                unit_cost=Decimal("-1"),
            )

    def test_lead_time_must_be_at_least_1(self):
        with pytest.raises(ValidationError) as exc_info:
            SupplierItemCreate(
                supplier_id=uuid4(),
                inventory_item_id=uuid4(),
                unit_cost=Decimal("1.00"),
                lead_time_days=0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("lead_time_days",) for e in errors)

    def test_lead_time_negative_raises(self):
        with pytest.raises(ValidationError):
            SupplierItemCreate(
                supplier_id=uuid4(),
                inventory_item_id=uuid4(),
                unit_cost=Decimal("1.00"),
                lead_time_days=-3,
            )


# ── SupplierItemUpdate ─────────────────────────────────────────────────────────


class TestSupplierItemUpdate:
    def test_all_optional(self):
        u = SupplierItemUpdate()
        assert u.unit_cost is None
        assert u.is_preferred is None
        assert u.is_active is None

    def test_partial_update(self):
        u = SupplierItemUpdate(unit_cost=Decimal("3.50"), is_preferred=True)
        assert u.unit_cost == Decimal("3.50")

    def test_unit_cost_zero_raises(self):
        with pytest.raises(ValidationError):
            SupplierItemUpdate(unit_cost=Decimal("0"))

    def test_lead_time_zero_raises(self):
        with pytest.raises(ValidationError):
            SupplierItemUpdate(lead_time_days=0)

    def test_model_dump_exclude_unset(self):
        u = SupplierItemUpdate(supplier_ref="NEW-REF")
        d = u.model_dump(exclude_unset=True)
        assert list(d.keys()) == ["supplier_ref"]


# ── PurchaseOrderLineCreate ────────────────────────────────────────────────────


class TestPurchaseOrderLineCreate:
    def test_with_inventory_item(self):
        line = PurchaseOrderLineCreate(
            inventory_item_id=uuid4(),
            quantity=Decimal("10"),
            unit_cost=Decimal("2.50"),
        )
        assert line.quantity == Decimal("10")
        assert line.unit_cost == Decimal("2.50")

    def test_with_description_only(self):
        line = PurchaseOrderLineCreate(
            description="Tornillos M6",
            quantity=Decimal("100"),
            unit_cost=Decimal("0.05"),
        )
        assert line.inventory_item_id is None
        assert line.description == "Tornillos M6"

    def test_missing_both_item_and_description_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PurchaseOrderLineCreate(quantity=Decimal("1"), unit_cost=Decimal("1.00"))
        errors = exc_info.value.errors()
        assert any("Se requiere un artículo" in str(e.get("msg", "")) for e in errors)

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError) as exc_info:
            PurchaseOrderLineCreate(
                description="X",
                quantity=Decimal("0"),
                unit_cost=Decimal("1.00"),
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("quantity",) for e in errors)

    def test_quantity_negative_raises(self):
        with pytest.raises(ValidationError):
            PurchaseOrderLineCreate(
                description="X",
                quantity=Decimal("-5"),
                unit_cost=Decimal("1.00"),
            )

    def test_unit_cost_zero_is_valid(self):
        # Free items / zero-cost samples are allowed
        line = PurchaseOrderLineCreate(
            description="Muestra gratuita",
            quantity=Decimal("1"),
            unit_cost=Decimal("0"),
        )
        assert line.unit_cost == Decimal("0")

    def test_unit_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            PurchaseOrderLineCreate(
                description="X",
                quantity=Decimal("1"),
                unit_cost=Decimal("-1"),
            )

    def test_description_max_length(self):
        with pytest.raises(ValidationError):
            PurchaseOrderLineCreate(
                description="A" * 256,
                quantity=Decimal("1"),
                unit_cost=Decimal("1.00"),
            )

    def test_description_255_chars_is_valid(self):
        line = PurchaseOrderLineCreate(
            description="A" * 255,
            quantity=Decimal("1"),
            unit_cost=Decimal("1.00"),
        )
        assert len(line.description) == 255


# ── PurchaseOrderCreate ────────────────────────────────────────────────────────


class TestPurchaseOrderCreate:
    def _valid_line(self) -> PurchaseOrderLineCreate:
        return PurchaseOrderLineCreate(
            description="Cable",
            quantity=Decimal("5"),
            unit_cost=Decimal("1.20"),
        )

    def test_valid_minimal(self):
        p = PurchaseOrderCreate(
            supplier_id=uuid4(),
            order_date=date.today(),
            lines=[self._valid_line()],
        )
        assert p.expected_date is None
        assert p.notes is None
        assert len(p.lines) == 1

    def test_lines_must_be_non_empty(self):
        with pytest.raises(ValidationError) as exc_info:
            PurchaseOrderCreate(
                supplier_id=uuid4(),
                order_date=date.today(),
                lines=[],
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("lines",) for e in errors)

    def test_multiple_lines(self):
        p = PurchaseOrderCreate(
            supplier_id=uuid4(),
            order_date=date.today(),
            lines=[self._valid_line(), self._valid_line(), self._valid_line()],
        )
        assert len(p.lines) == 3

    def test_with_all_fields(self):
        p = PurchaseOrderCreate(
            supplier_id=uuid4(),
            order_date=date(2026, 1, 15),
            expected_date=date(2026, 1, 22),
            notes="Urgente",
            lines=[self._valid_line()],
        )
        assert p.expected_date == date(2026, 1, 22)
        assert p.notes == "Urgente"


# ── PurchaseOrderUpdate ────────────────────────────────────────────────────────


class TestPurchaseOrderUpdate:
    def test_all_optional(self):
        u = PurchaseOrderUpdate()
        assert u.expected_date is None
        assert u.notes is None

    def test_partial_update(self):
        u = PurchaseOrderUpdate(notes="Nueva nota")
        assert u.notes == "Nueva nota"

    def test_model_dump_exclude_unset(self):
        u = PurchaseOrderUpdate(expected_date=date(2026, 3, 1))
        d = u.model_dump(exclude_unset=True)
        assert list(d.keys()) == ["expected_date"]


# ── PurchaseOrderResponse computed total ──────────────────────────────────────


class TestPurchaseOrderResponseTotal:
    def _make_line_response(self, subtotal: Decimal) -> dict:
        return dict(
            id=uuid4(),
            purchase_order_id=uuid4(),
            inventory_item_id=None,
            description="Item",
            quantity=Decimal("1"),
            unit_cost=subtotal,
            subtotal=subtotal,
            created_at=_now(),
            updated_at=_now(),
        )

    def test_total_computed_from_lines(self):
        r = PurchaseOrderResponse(
            id=uuid4(),
            supplier_id=uuid4(),
            order_number="PED-2026-0001",
            status="pending",
            order_date=date.today(),
            expected_date=None,
            received_date=None,
            notes=None,
            lines=[
                self._make_line_response(Decimal("10.00")),
                self._make_line_response(Decimal("5.50")),
            ],
            created_at=_now(),
            updated_at=_now(),
        )
        assert r.total == Decimal("15.50")

    def test_total_empty_lines_is_zero(self):
        r = PurchaseOrderResponse(
            id=uuid4(),
            supplier_id=uuid4(),
            order_number="PED-2026-0002",
            status="pending",
            order_date=date.today(),
            expected_date=None,
            received_date=None,
            notes=None,
            lines=[],
            created_at=_now(),
            updated_at=_now(),
        )
        assert r.total == Decimal("0")


class TestPurchaseOrderSummary:
    def test_default_total_zero(self):
        s = PurchaseOrderSummary(
            id=uuid4(),
            supplier_id=uuid4(),
            order_number="PED-2026-0003",
            status="pending",
            order_date=date.today(),
            expected_date=None,
            received_date=None,
            created_at=_now(),
            updated_at=_now(),
        )
        assert s.total == Decimal("0")

    def test_total_can_be_set(self):
        s = PurchaseOrderSummary(
            id=uuid4(),
            supplier_id=uuid4(),
            order_number="PED-2026-0004",
            status="received",
            order_date=date.today(),
            expected_date=None,
            received_date=date.today(),
            created_at=_now(),
            updated_at=_now(),
            total=Decimal("100.25"),
        )
        assert s.total == Decimal("100.25")


class TestPurchaseOrderListResponse:
    def test_empty(self):
        r = PurchaseOrderListResponse(items=[], total=0, skip=0, limit=50)
        assert r.total == 0

    def test_pagination(self):
        r = PurchaseOrderListResponse(items=[], total=200, skip=50, limit=25)
        assert r.skip == 50
        assert r.limit == 25
