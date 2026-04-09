"""
Unit tests for Inventory Pydantic schemas.

Pure Python — no database, no mocks, no async.
Covers: InventoryItemCreate, InventoryItemCreateWithSupplier, InventoryItemUpdate,
        InventoryItemBrief, InventoryItemResponse, InventoryItemListResponse,
        StockMovementCreate, StockMovementResponse, ManualAdjustmentRequest.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.inventory_item import (
    InventoryItemBrief,
    InventoryItemCreate,
    InventoryItemCreateWithSupplier,
    InventoryItemListResponse,
    InventoryItemResponse,
    InventoryItemUpdate,
)
from app.schemas.stock_movement import (
    ManualAdjustmentRequest,
    StockMovementCreate,
    StockMovementResponse,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── InventoryItemCreate ────────────────────────────────────────────────────────

class TestInventoryItemCreate:
    def test_defaults(self):
        data = InventoryItemCreate(name="Cable 2.5mm")
        assert data.unit == "ud"
        assert data.unit_cost == Decimal("0")
        assert data.unit_price == Decimal("0")
        assert data.stock_current == Decimal("0")
        assert data.stock_min == Decimal("0")
        assert data.description is None
        assert data.supplier_id is None

    def test_name_is_required(self):
        with pytest.raises(ValidationError):
            InventoryItemCreate()

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            InventoryItemCreate(name="x" * 256)

    def test_name_at_max_length(self):
        data = InventoryItemCreate(name="x" * 255)
        assert len(data.name) == 255

    def test_unit_max_length(self):
        with pytest.raises(ValidationError):
            InventoryItemCreate(name="Cable", unit="x" * 21)

    def test_unit_at_max_length(self):
        data = InventoryItemCreate(name="Cable", unit="x" * 20)
        assert len(data.unit) == 20

    def test_unit_cost_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            InventoryItemCreate(name="Cable", unit_cost=Decimal("-1"))

    def test_unit_price_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            InventoryItemCreate(name="Cable", unit_price=Decimal("-0.01"))

    def test_stock_current_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            InventoryItemCreate(name="Cable", stock_current=Decimal("-5"))

    def test_stock_min_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            InventoryItemCreate(name="Cable", stock_min=Decimal("-1"))

    def test_zero_values_allowed(self):
        data = InventoryItemCreate(
            name="Cable",
            unit_cost=Decimal("0"),
            unit_price=Decimal("0"),
            stock_current=Decimal("0"),
            stock_min=Decimal("0"),
        )
        assert data.unit_cost == Decimal("0")

    def test_all_fields(self):
        supplier_id = uuid.uuid4()
        data = InventoryItemCreate(
            name="Cable 2.5mm²",
            description="Cable de cobre",
            unit="m",
            unit_cost=Decimal("1.50"),
            unit_price=Decimal("2.20"),
            stock_current=Decimal("100"),
            stock_min=Decimal("20"),
            supplier_id=supplier_id,
        )
        assert data.name == "Cable 2.5mm²"
        assert data.unit == "m"
        assert data.unit_cost == Decimal("1.50")
        assert data.supplier_id == supplier_id


# ── InventoryItemCreateWithSupplier ───────────────────────────────────────────

class TestInventoryItemCreateWithSupplier:
    def test_defaults(self):
        data = InventoryItemCreateWithSupplier(name="Interruptor")
        assert data.unit == "ud"
        assert data.unit_price == Decimal("0")
        assert data.stock_min == Decimal("0")
        assert data.is_active is True
        assert data.supplier_id is None
        assert data.unit_cost == Decimal("0")
        assert data.supplier_ref is None
        assert data.is_preferred is True

    def test_name_is_required(self):
        with pytest.raises(ValidationError):
            InventoryItemCreateWithSupplier()

    def test_unit_price_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            InventoryItemCreateWithSupplier(name="X", unit_price=Decimal("-1"))

    def test_unit_cost_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            InventoryItemCreateWithSupplier(name="X", unit_cost=Decimal("-0.01"))

    def test_stock_min_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            InventoryItemCreateWithSupplier(name="X", stock_min=Decimal("-5"))

    def test_full_creation_with_supplier(self):
        supplier_id = uuid.uuid4()
        data = InventoryItemCreateWithSupplier(
            name="Interruptor Schneider",
            description="Interruptor magnetotérmico 10A",
            unit="ud",
            unit_price=Decimal("12.50"),
            stock_min=Decimal("5"),
            supplier_id=supplier_id,
            unit_cost=Decimal("7.80"),
            supplier_ref="SNE-MT-10A",
            is_preferred=True,
        )
        assert data.supplier_id == supplier_id
        assert data.supplier_ref == "SNE-MT-10A"

    def test_deactivated_on_create(self):
        data = InventoryItemCreateWithSupplier(name="X", is_active=False)
        assert data.is_active is False


# ── InventoryItemUpdate ────────────────────────────────────────────────────────

class TestInventoryItemUpdate:
    def test_all_fields_optional(self):
        data = InventoryItemUpdate()
        assert data.model_fields_set == set()

    def test_partial_update_tracks_set_fields(self):
        data = InventoryItemUpdate(name="Nuevo nombre")
        assert "name" in data.model_fields_set
        assert "unit" not in data.model_fields_set

    def test_name_max_length_enforced(self):
        with pytest.raises(ValidationError):
            InventoryItemUpdate(name="x" * 256)

    def test_unit_max_length_enforced(self):
        with pytest.raises(ValidationError):
            InventoryItemUpdate(unit="x" * 21)

    def test_unit_cost_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            InventoryItemUpdate(unit_cost=Decimal("-1"))

    def test_unit_price_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            InventoryItemUpdate(unit_price=Decimal("-0.01"))

    def test_stock_min_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            InventoryItemUpdate(stock_min=Decimal("-1"))

    def test_deactivate_via_update(self):
        data = InventoryItemUpdate(is_active=False)
        assert data.is_active is False

    def test_model_dump_exclude_unset(self):
        data = InventoryItemUpdate(name="Cable 6mm", stock_min=Decimal("10"))
        dumped = data.model_dump(exclude_unset=True)
        assert dumped == {"name": "Cable 6mm", "stock_min": Decimal("10")}

    def test_stock_current_not_in_schema(self):
        # stock_current must not be modifiable via update — only via movements
        assert "stock_current" not in InventoryItemUpdate.model_fields


# ── InventoryItemBrief ─────────────────────────────────────────────────────────

class TestInventoryItemBrief:
    def _make_brief(self, **kwargs) -> InventoryItemBrief:
        defaults = dict(
            id=uuid.uuid4(),
            name="Cable 2.5mm",
            description=None,
            unit="m",
            unit_cost=Decimal("1.50"),
            unit_price=Decimal("2.20"),
            stock_current=Decimal("100"),
            stock_min=Decimal("20"),
            is_active=True,
        )
        defaults.update(kwargs)
        return InventoryItemBrief(**defaults)

    def test_basic_creation(self):
        brief = self._make_brief()
        assert brief.name == "Cable 2.5mm"
        assert brief.is_active is True

    def test_optional_description(self):
        brief = self._make_brief(description=None)
        assert brief.description is None

    def test_with_description(self):
        brief = self._make_brief(description="Cable de cobre para instalaciones")
        assert brief.description == "Cable de cobre para instalaciones"

    def test_inactive_item(self):
        brief = self._make_brief(is_active=False)
        assert brief.is_active is False


# ── InventoryItemResponse ──────────────────────────────────────────────────────

class TestInventoryItemResponse:
    def _make_response(self, **kwargs) -> InventoryItemResponse:
        now = _now()
        defaults = dict(
            id=uuid.uuid4(),
            name="Cable 2.5mm",
            description=None,
            unit="m",
            unit_cost=Decimal("1.50"),
            unit_cost_avg=Decimal("1.45"),
            unit_price=Decimal("2.20"),
            stock_current=Decimal("100"),
            stock_min=Decimal("20"),
            supplier_id=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        defaults.update(kwargs)
        return InventoryItemResponse(**defaults)

    def test_computed_field_defaults(self):
        response = self._make_response()
        assert response.stock_reserved == Decimal("0")
        assert response.stock_available == Decimal("0")
        assert response.low_stock_alert is False
        assert response.last_movement_at is None
        assert response.supplier_items == []
        assert response.preferred_supplier is None

    def test_stock_available_field(self):
        response = self._make_response(
            stock_current=Decimal("50"),
            stock_reserved=Decimal("10"),
            stock_available=Decimal("40"),
        )
        assert response.stock_available == Decimal("40")

    def test_low_stock_alert_true(self):
        response = self._make_response(
            stock_current=Decimal("5"),
            stock_reserved=Decimal("0"),
            stock_available=Decimal("5"),
            stock_min=Decimal("10"),
            low_stock_alert=True,
        )
        assert response.low_stock_alert is True

    def test_low_stock_alert_false_when_above_min(self):
        response = self._make_response(
            stock_current=Decimal("100"),
            stock_reserved=Decimal("5"),
            stock_available=Decimal("95"),
            stock_min=Decimal("20"),
            low_stock_alert=False,
        )
        assert response.low_stock_alert is False

    def test_with_supplier_id(self):
        supplier_id = uuid.uuid4()
        response = self._make_response(supplier_id=supplier_id)
        assert response.supplier_id == supplier_id

    def test_unit_cost_avg_field(self):
        response = self._make_response(unit_cost_avg=Decimal("1.6789"))
        assert response.unit_cost_avg == Decimal("1.6789")

    def test_last_movement_at(self):
        ts = _now()
        response = self._make_response(last_movement_at=ts)
        assert response.last_movement_at == ts

    def test_inactive_item(self):
        response = self._make_response(is_active=False)
        assert response.is_active is False


# ── InventoryItemListResponse ──────────────────────────────────────────────────

class TestInventoryItemListResponse:
    def test_empty_list(self):
        response = InventoryItemListResponse(items=[], total=0, skip=0, limit=50)
        assert response.total == 0
        assert response.items == []

    def test_pagination_fields(self):
        response = InventoryItemListResponse(items=[], total=200, skip=50, limit=25)
        assert response.total == 200
        assert response.skip == 50
        assert response.limit == 25


# ── StockMovementCreate ────────────────────────────────────────────────────────

class TestStockMovementCreate:
    def test_entry_movement(self):
        data = StockMovementCreate(
            inventory_item_id=uuid.uuid4(),
            movement_type="entry",
            quantity=Decimal("50"),
            unit_cost=Decimal("1.50"),
            reference_type="purchase_order",
        )
        assert data.movement_type == "entry"
        assert data.quantity == Decimal("50")

    def test_exit_movement(self):
        data = StockMovementCreate(
            inventory_item_id=uuid.uuid4(),
            movement_type="exit",
            quantity=Decimal("10"),
            unit_cost=Decimal("1.50"),
            reference_type="work_order",
        )
        assert data.movement_type == "exit"

    def test_manual_adjustment_reference_type(self):
        data = StockMovementCreate(
            inventory_item_id=uuid.uuid4(),
            movement_type="entry",
            quantity=Decimal("5"),
            unit_cost=Decimal("2.00"),
            reference_type="manual_adjustment",
        )
        assert data.reference_type == "manual_adjustment"

    def test_invalid_movement_type_raises(self):
        with pytest.raises(ValidationError):
            StockMovementCreate(
                inventory_item_id=uuid.uuid4(),
                movement_type="correction",
                quantity=Decimal("10"),
                unit_cost=Decimal("1.00"),
                reference_type="manual_adjustment",
            )

    def test_invalid_reference_type_raises(self):
        with pytest.raises(ValidationError):
            StockMovementCreate(
                inventory_item_id=uuid.uuid4(),
                movement_type="entry",
                quantity=Decimal("10"),
                unit_cost=Decimal("1.00"),
                reference_type="unknown_type",
            )

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            StockMovementCreate(
                inventory_item_id=uuid.uuid4(),
                movement_type="entry",
                quantity=Decimal("0"),
                unit_cost=Decimal("1.00"),
                reference_type="manual_adjustment",
            )

    def test_quantity_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            StockMovementCreate(
                inventory_item_id=uuid.uuid4(),
                movement_type="entry",
                quantity=Decimal("-5"),
                unit_cost=Decimal("1.00"),
                reference_type="manual_adjustment",
            )

    def test_unit_cost_must_be_positive(self):
        with pytest.raises(ValidationError):
            StockMovementCreate(
                inventory_item_id=uuid.uuid4(),
                movement_type="entry",
                quantity=Decimal("10"),
                unit_cost=Decimal("0"),
                reference_type="manual_adjustment",
            )

    def test_unit_cost_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            StockMovementCreate(
                inventory_item_id=uuid.uuid4(),
                movement_type="exit",
                quantity=Decimal("10"),
                unit_cost=Decimal("-1.00"),
                reference_type="work_order",
            )

    def test_optional_reference_id(self):
        ref_id = uuid.uuid4()
        data = StockMovementCreate(
            inventory_item_id=uuid.uuid4(),
            movement_type="entry",
            quantity=Decimal("50"),
            unit_cost=Decimal("1.50"),
            reference_type="purchase_order",
            reference_id=ref_id,
        )
        assert data.reference_id == ref_id

    def test_reference_id_defaults_to_none(self):
        data = StockMovementCreate(
            inventory_item_id=uuid.uuid4(),
            movement_type="entry",
            quantity=Decimal("5"),
            unit_cost=Decimal("1.00"),
            reference_type="manual_adjustment",
        )
        assert data.reference_id is None

    def test_optional_notes(self):
        data = StockMovementCreate(
            inventory_item_id=uuid.uuid4(),
            movement_type="entry",
            quantity=Decimal("10"),
            unit_cost=Decimal("2.00"),
            reference_type="manual_adjustment",
            notes="Reposición trimestral",
        )
        assert data.notes == "Reposición trimestral"


# ── StockMovementResponse ──────────────────────────────────────────────────────

class TestStockMovementResponse:
    def _make_response(self, **kwargs) -> StockMovementResponse:
        defaults = dict(
            id=uuid.uuid4(),
            inventory_item_id=uuid.uuid4(),
            inventory_item_name="Cable 2.5mm",
            movement_type="entry",
            quantity=Decimal("50"),
            unit_cost=Decimal("1.50"),
            reference_type="purchase_order",
            reference_id=None,
            notes=None,
            created_at=_now(),
        )
        defaults.update(kwargs)
        return StockMovementResponse(**defaults)

    def test_entry_movement_response(self):
        response = self._make_response(movement_type="entry")
        assert response.movement_type == "entry"

    def test_exit_movement_response(self):
        response = self._make_response(movement_type="exit")
        assert response.movement_type == "exit"

    def test_reference_id_nullable(self):
        response = self._make_response(reference_id=None)
        assert response.reference_id is None

    def test_with_reference_id(self):
        ref_id = uuid.uuid4()
        response = self._make_response(reference_id=ref_id)
        assert response.reference_id == ref_id

    def test_notes_nullable(self):
        response = self._make_response(notes=None)
        assert response.notes is None

    def test_item_name_populated(self):
        response = self._make_response(inventory_item_name="Interruptor 10A")
        assert response.inventory_item_name == "Interruptor 10A"


# ── ManualAdjustmentRequest ────────────────────────────────────────────────────

class TestManualAdjustmentRequest:
    def test_positive_quantity_is_entry(self):
        data = ManualAdjustmentRequest(
            quantity=Decimal("10"),
            unit_cost=Decimal("2.00"),
            notes="Corrección de inventario por conteo físico",
        )
        assert data.quantity == Decimal("10")

    def test_negative_quantity_is_downward_correction(self):
        data = ManualAdjustmentRequest(
            quantity=Decimal("-5"),
            unit_cost=Decimal("2.00"),
            notes="Ajuste por rotura de material",
        )
        assert data.quantity == Decimal("-5")

    def test_quantity_cannot_be_zero(self):
        with pytest.raises(ValidationError):
            ManualAdjustmentRequest(
                quantity=Decimal("0"),
                unit_cost=Decimal("2.00"),
                notes="Notas de ajuste",
            )

    def test_unit_cost_must_be_positive(self):
        with pytest.raises(ValidationError):
            ManualAdjustmentRequest(
                quantity=Decimal("5"),
                unit_cost=Decimal("0"),
                notes="Notas de ajuste",
            )

    def test_unit_cost_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            ManualAdjustmentRequest(
                quantity=Decimal("5"),
                unit_cost=Decimal("-1.00"),
                notes="Notas de ajuste",
            )

    def test_notes_are_required(self):
        with pytest.raises(ValidationError):
            ManualAdjustmentRequest(
                quantity=Decimal("5"),
                unit_cost=Decimal("2.00"),
            )

    def test_notes_min_length_enforced(self):
        with pytest.raises(ValidationError):
            ManualAdjustmentRequest(
                quantity=Decimal("5"),
                unit_cost=Decimal("2.00"),
                notes="xyzw",  # 4 chars — below min_length=5
            )

    def test_notes_exactly_min_length(self):
        data = ManualAdjustmentRequest(
            quantity=Decimal("5"),
            unit_cost=Decimal("2.00"),
            notes="12345",  # exactly 5 chars
        )
        assert len(data.notes) == 5

    def test_full_adjustment_fields(self):
        data = ManualAdjustmentRequest(
            quantity=Decimal("25.500"),
            unit_cost=Decimal("3.7500"),
            notes="Reposición urgente por falta de stock",
        )
        assert data.quantity == Decimal("25.500")
        assert data.unit_cost == Decimal("3.7500")
        assert "urgente" in data.notes
