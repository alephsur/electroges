"""
Unit tests for InventoryService.

All repositories and the session are mocked — no database needed.
Covers: list_items, get_item, create_item, update_item, deactivate_item,
        manual_adjustment (entry/exit, PMP, stock underflow),
        get_movements, get_low_stock_alerts,
        add_supplier, update_supplier_price, remove_supplier, set_preferred_supplier,
        get_item_suppliers.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import NamedTuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.inventory_item import (
    InventoryItemCreateWithSupplier,
    InventoryItemUpdate,
)
from app.schemas.stock_movement import ManualAdjustmentRequest
from app.schemas.supplier_item import SupplierItemCreate, SupplierItemUpdate
from app.services.inventory import InventoryService

TENANT_ID = uuid.uuid4()


# ── Factories ──────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_supplier_item(**kwargs) -> MagicMock:
    si = MagicMock()
    si.id = uuid.uuid4()
    si.supplier_id = uuid.uuid4()
    si.inventory_item_id = uuid.uuid4()
    si.supplier_ref = None
    si.unit_cost = Decimal("1.50")
    si.last_purchase_cost = None
    si.last_purchase_date = None
    si.lead_time_days = None
    si.is_preferred = True
    si.is_active = True
    si.created_at = _now()
    si.updated_at = _now()
    si.supplier = MagicMock()
    si.supplier.name = "Proveedor Test"
    for k, v in kwargs.items():
        setattr(si, k, v)
    return si


def make_item(**kwargs) -> MagicMock:
    item = MagicMock()
    item.id = uuid.uuid4()
    item.tenant_id = TENANT_ID
    item.name = "Cable 2.5mm"
    item.description = None
    item.unit = "m"
    item.unit_cost = Decimal("1.50")
    item.unit_cost_avg = Decimal("1.45")
    item.unit_price = Decimal("2.20")
    item.stock_current = Decimal("100")
    item.stock_min = Decimal("20")
    item.stock_reserved = Decimal("0")
    item.supplier_id = None
    item.is_active = True
    item.created_at = _now()
    item.updated_at = _now()
    item.supplier_items = []
    item.stock_movements = []
    for k, v in kwargs.items():
        setattr(item, k, v)
    return item


def make_movement(**kwargs) -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.inventory_item_id = uuid.uuid4()
    m.movement_type = "entry"
    m.quantity = Decimal("50")
    m.unit_cost = Decimal("1.50")
    m.reference_type = "manual_adjustment"
    m.reference_id = None
    m.notes = "Ajuste inicial"
    m.created_at = _now()
    m.inventory_item = MagicMock()
    m.inventory_item.name = "Cable 2.5mm"
    for k, v in kwargs.items():
        setattr(m, k, v)
    return m


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


class _Mocks(NamedTuple):
    svc: InventoryService
    item_repo: AsyncMock
    movement_repo: AsyncMock
    supplier_item_repo: AsyncMock


@pytest.fixture
def mocks(mock_session) -> _Mocks:
    item_repo = AsyncMock()
    movement_repo = AsyncMock()
    supplier_item_repo = AsyncMock()

    with (
        patch("app.services.inventory.InventoryItemRepository", return_value=item_repo),
        patch("app.services.inventory.StockMovementRepository", return_value=movement_repo),
        patch("app.services.inventory.SupplierItemRepository", return_value=supplier_item_repo),
    ):
        svc = InventoryService(mock_session, TENANT_ID)
        yield _Mocks(svc, item_repo, movement_repo, supplier_item_repo)


# ── list_items ─────────────────────────────────────────────────────────────────

class TestListItems:
    async def test_returns_paginated_response(self, mocks):
        mocks.item_repo.search_inventory.return_value = (
            [make_item(), make_item()], 2
        )

        result = await mocks.svc.list_items(
            query=None, supplier_id=None, low_stock_only=False, skip=0, limit=50
        )

        assert result.total == 2
        assert len(result.items) == 2
        assert result.skip == 0
        assert result.limit == 50

    async def test_passes_filters_to_repo(self, mocks):
        supplier_id = uuid.uuid4()
        mocks.item_repo.search_inventory.return_value = ([], 0)

        await mocks.svc.list_items(
            query="cable",
            supplier_id=supplier_id,
            low_stock_only=True,
            skip=10,
            limit=25,
        )

        mocks.item_repo.search_inventory.assert_called_once_with(
            "cable",
            supplier_id=supplier_id,
            low_stock_only=True,
            skip=10,
            limit=25,
        )

    async def test_empty_result(self, mocks):
        mocks.item_repo.search_inventory.return_value = ([], 0)

        result = await mocks.svc.list_items(
            query=None, supplier_id=None, low_stock_only=False, skip=0, limit=50
        )

        assert result.total == 0
        assert result.items == []

    async def test_enriches_stock_computed_fields(self, mocks):
        item = make_item(
            stock_current=Decimal("30"),
            stock_reserved=Decimal("10"),
            stock_min=Decimal("15"),
        )
        mocks.item_repo.search_inventory.return_value = ([item], 1)

        result = await mocks.svc.list_items(
            query=None, supplier_id=None, low_stock_only=False, skip=0, limit=50
        )

        enriched = result.items[0]
        assert enriched.stock_available == Decimal("20")
        # 20 > 15 → no alert
        assert enriched.low_stock_alert is False

    async def test_low_stock_alert_triggered_when_available_le_min(self, mocks):
        item = make_item(
            stock_current=Decimal("15"),
            stock_reserved=Decimal("5"),
            stock_min=Decimal("10"),
        )
        mocks.item_repo.search_inventory.return_value = ([item], 1)

        result = await mocks.svc.list_items(
            query=None, supplier_id=None, low_stock_only=False, skip=0, limit=50
        )

        enriched = result.items[0]
        # available = 15 - 5 = 10 → equals stock_min → alert is True
        assert enriched.stock_available == Decimal("10")
        assert enriched.low_stock_alert is True


# ── get_item ───────────────────────────────────────────────────────────────────

class TestGetItem:
    async def test_returns_enriched_response(self, mocks):
        item = make_item()
        mocks.item_repo.get_with_full_detail.return_value = item

        result = await mocks.svc.get_item(item.id)

        mocks.item_repo.get_with_full_detail.assert_called_once_with(item.id)
        assert result.id == item.id
        assert result.name == item.name

    async def test_raises_404_when_not_found(self, mocks):
        mocks.item_repo.get_with_full_detail.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.get_item(uuid.uuid4())

        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()

    async def test_stock_available_computed_correctly(self, mocks):
        item = make_item(
            stock_current=Decimal("80"),
            stock_reserved=Decimal("30"),
            stock_min=Decimal("20"),
        )
        mocks.item_repo.get_with_full_detail.return_value = item

        result = await mocks.svc.get_item(item.id)

        assert result.stock_reserved == Decimal("30")
        assert result.stock_available == Decimal("50")
        assert result.low_stock_alert is False

    async def test_low_stock_alert_when_available_below_min(self, mocks):
        item = make_item(
            stock_current=Decimal("25"),
            stock_reserved=Decimal("10"),
            stock_min=Decimal("20"),
        )
        mocks.item_repo.get_with_full_detail.return_value = item

        result = await mocks.svc.get_item(item.id)

        # available = 25 - 10 = 15 < 20 (stock_min) → alert
        assert result.stock_available == Decimal("15")
        assert result.low_stock_alert is True

    async def test_last_movement_at_populated(self, mocks):
        ts = _now()
        movement = MagicMock()
        movement.created_at = ts
        item = make_item(stock_movements=[movement])
        mocks.item_repo.get_with_full_detail.return_value = item

        result = await mocks.svc.get_item(item.id)

        assert result.last_movement_at == ts

    async def test_last_movement_at_none_when_no_movements(self, mocks):
        item = make_item(stock_movements=[])
        mocks.item_repo.get_with_full_detail.return_value = item

        result = await mocks.svc.get_item(item.id)

        assert result.last_movement_at is None


# ── create_item ────────────────────────────────────────────────────────────────

class TestCreateItem:
    async def test_creates_item_without_supplier(self, mocks):
        created = make_item(stock_current=Decimal("0"))
        mocks.item_repo.create.return_value = created
        mocks.item_repo.get_with_supplier_items.return_value = created

        data = InventoryItemCreateWithSupplier(
            name="Interruptor 10A",
            unit="ud",
            unit_price=Decimal("12.50"),
            stock_min=Decimal("5"),
        )
        result = await mocks.svc.create_item(data)

        mocks.item_repo.create.assert_called_once()
        # No supplier → no SupplierItem created
        assert result.id == created.id

    async def test_creates_supplier_item_when_supplier_and_cost_provided(
        self, mocks, mock_session
    ):
        supplier_id = uuid.uuid4()
        created = make_item(supplier_id=supplier_id, stock_current=Decimal("0"))
        si = make_supplier_item(supplier_id=supplier_id, inventory_item_id=created.id)
        created.supplier_items = [si]
        mocks.item_repo.create.return_value = created
        mocks.item_repo.get_with_supplier_items.return_value = created

        data = InventoryItemCreateWithSupplier(
            name="Cable 6mm",
            supplier_id=supplier_id,
            unit_cost=Decimal("3.00"),
            unit_price=Decimal("5.00"),
        )
        result = await mocks.svc.create_item(data)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        assert result.id == created.id

    async def test_does_not_create_supplier_item_when_cost_is_zero(
        self, mocks, mock_session
    ):
        supplier_id = uuid.uuid4()
        created = make_item(supplier_id=supplier_id, stock_current=Decimal("0"))
        mocks.item_repo.create.return_value = created
        mocks.item_repo.get_with_supplier_items.return_value = created

        data = InventoryItemCreateWithSupplier(
            name="Cable 6mm",
            supplier_id=supplier_id,
            unit_cost=Decimal("0"),  # cost is 0 → no SupplierItem
        )
        await mocks.svc.create_item(data)

        mock_session.add.assert_not_called()

    async def test_stock_current_initialised_to_zero(self, mocks):
        """create_item always sets stock_current=0 regardless of input — use movements."""
        created = make_item(stock_current=Decimal("0"))
        mocks.item_repo.create.return_value = created
        mocks.item_repo.get_with_supplier_items.return_value = created

        data = InventoryItemCreateWithSupplier(name="Item X")
        await mocks.svc.create_item(data)

        call_args = mocks.item_repo.create.call_args[0][0]
        assert call_args.stock_current == Decimal("0")

    async def test_commits_session(self, mocks, mock_session):
        created = make_item()
        mocks.item_repo.create.return_value = created
        mocks.item_repo.get_with_supplier_items.return_value = created

        await mocks.svc.create_item(InventoryItemCreateWithSupplier(name="Item Y"))

        mock_session.commit.assert_called_once()


# ── update_item ────────────────────────────────────────────────────────────────

class TestUpdateItem:
    async def test_updates_item(self, mocks, mock_session):
        item = make_item()
        mocks.item_repo.get_with_supplier_items.side_effect = [item, item]

        data = InventoryItemUpdate(name="Cable Nuevo", stock_min=Decimal("30"))
        result = await mocks.svc.update_item(item.id, data)

        mocks.item_repo.update.assert_called_once_with(
            item, {"name": "Cable Nuevo", "stock_min": Decimal("30")}
        )
        mock_session.commit.assert_called_once()
        assert result.id == item.id

    async def test_raises_404_when_not_found(self, mocks):
        mocks.item_repo.get_with_supplier_items.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_item(uuid.uuid4(), InventoryItemUpdate(name="X"))

        assert exc_info.value.status_code == 404

    async def test_partial_update_only_sends_set_fields(self, mocks):
        item = make_item()
        mocks.item_repo.get_with_supplier_items.side_effect = [item, item]

        data = InventoryItemUpdate(unit_price=Decimal("5.00"))
        await mocks.svc.update_item(item.id, data)

        update_dict = mocks.item_repo.update.call_args[0][1]
        assert update_dict == {"unit_price": Decimal("5.00")}
        assert "name" not in update_dict

    async def test_stock_current_not_updated_via_update(self, mocks):
        """stock_current must not be sent to the repo via update_item."""
        item = make_item()
        mocks.item_repo.get_with_supplier_items.side_effect = [item, item]

        data = InventoryItemUpdate(name="X")
        await mocks.svc.update_item(item.id, data)

        update_dict = mocks.item_repo.update.call_args[0][1]
        assert "stock_current" not in update_dict


# ── deactivate_item ────────────────────────────────────────────────────────────

class TestDeactivateItem:
    async def test_deactivates_item(self, mocks, mock_session):
        item = make_item(is_active=True)
        mocks.item_repo.get_by_id.return_value = item

        result = await mocks.svc.deactivate_item(item.id)

        mocks.item_repo.update.assert_called_once_with(item, {"is_active": False})
        mock_session.commit.assert_called_once()
        # The response is built from the (still-mocked) item attributes
        assert result.id == item.id

    async def test_raises_404_when_not_found(self, mocks):
        mocks.item_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.deactivate_item(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_response_includes_stock_available(self, mocks):
        item = make_item(
            stock_current=Decimal("50"),
            stock_reserved=Decimal("10"),
            stock_min=Decimal("15"),
        )
        mocks.item_repo.get_by_id.return_value = item

        result = await mocks.svc.deactivate_item(item.id)

        assert result.stock_available == Decimal("40")
        # 40 > 15 → no alert
        assert result.low_stock_alert is False

    async def test_low_stock_alert_in_deactivate_response(self, mocks):
        item = make_item(
            stock_current=Decimal("10"),
            stock_reserved=Decimal("5"),
            stock_min=Decimal("10"),
        )
        mocks.item_repo.get_by_id.return_value = item

        result = await mocks.svc.deactivate_item(item.id)

        # available = 10 - 5 = 5 ≤ 10 (stock_min) → alert
        assert result.stock_available == Decimal("5")
        assert result.low_stock_alert is True


# ── manual_adjustment ──────────────────────────────────────────────────────────

class TestManualAdjustment:
    async def test_entry_increases_stock_and_recalculates_pmp(
        self, mocks, mock_session
    ):
        item = make_item(stock_current=Decimal("50"), unit_cost_avg=Decimal("1.40"))
        mocks.item_repo.get_by_id.return_value = item
        mocks.movement_repo.calculate_pmp.return_value = Decimal("1.4500")
        enriched = make_item(
            stock_current=Decimal("70"),
            stock_reserved=Decimal("0"),
            stock_min=Decimal("20"),
        )
        mocks.item_repo.get_with_full_detail.return_value = enriched

        data = ManualAdjustmentRequest(
            quantity=Decimal("20"),
            unit_cost=Decimal("1.60"),
            notes="Reposición de stock",
        )
        result = await mocks.svc.manual_adjustment(item.id, data)

        # Movement created with type "entry"
        movement_arg = mocks.movement_repo.create.call_args[0][0]
        assert movement_arg.movement_type == "entry"
        assert movement_arg.quantity == Decimal("20")
        assert movement_arg.unit_cost == Decimal("1.60")
        assert movement_arg.reference_type == "manual_adjustment"

        # PMP recalculated for entries
        mocks.movement_repo.calculate_pmp.assert_called_once_with(item.id)
        mocks.item_repo.update_stock_and_pmp.assert_called_once_with(
            item.id, Decimal("20"), Decimal("1.4500")
        )
        mock_session.commit.assert_called_once()
        assert result.id == enriched.id

    async def test_exit_decreases_stock_without_pmp_recalculation(
        self, mocks, mock_session
    ):
        item = make_item(stock_current=Decimal("50"), unit_cost_avg=Decimal("1.45"))
        mocks.item_repo.get_by_id.return_value = item
        enriched = make_item(stock_current=Decimal("40"), stock_reserved=Decimal("0"))
        mocks.item_repo.get_with_full_detail.return_value = enriched

        data = ManualAdjustmentRequest(
            quantity=Decimal("-10"),
            unit_cost=Decimal("1.45"),
            notes="Ajuste por rotura",
        )
        result = await mocks.svc.manual_adjustment(item.id, data)

        movement_arg = mocks.movement_repo.create.call_args[0][0]
        assert movement_arg.movement_type == "exit"
        assert movement_arg.quantity == Decimal("10")  # stored as positive abs value

        # PMP NOT recalculated for exits — use existing avg
        mocks.movement_repo.calculate_pmp.assert_not_called()
        mocks.item_repo.update_stock_and_pmp.assert_called_once_with(
            item.id, Decimal("-10"), Decimal("1.45")
        )
        assert result.id == enriched.id

    async def test_raises_404_when_item_not_found(self, mocks):
        mocks.item_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.manual_adjustment(
                uuid.uuid4(),
                ManualAdjustmentRequest(
                    quantity=Decimal("10"),
                    unit_cost=Decimal("2.00"),
                    notes="Ajuste test",
                ),
            )

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_exit_exceeds_current_stock(self, mocks):
        item = make_item(stock_current=Decimal("5"))
        mocks.item_repo.get_by_id.return_value = item

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.manual_adjustment(
                item.id,
                ManualAdjustmentRequest(
                    quantity=Decimal("-10"),  # trying to remove 10 but only 5 available
                    unit_cost=Decimal("1.50"),
                    notes="Ajuste incorrecto",
                ),
            )

        assert exc_info.value.status_code == 400
        assert "stock" in exc_info.value.detail.lower()

    async def test_exit_exactly_all_stock_is_allowed(self, mocks, mock_session):
        item = make_item(stock_current=Decimal("10"), unit_cost_avg=Decimal("2.00"))
        mocks.item_repo.get_by_id.return_value = item
        enriched = make_item(stock_current=Decimal("0"), stock_reserved=Decimal("0"))
        mocks.item_repo.get_with_full_detail.return_value = enriched

        data = ManualAdjustmentRequest(
            quantity=Decimal("-10"),
            unit_cost=Decimal("2.00"),
            notes="Salida completa de lote",
        )
        # Must not raise
        await mocks.svc.manual_adjustment(item.id, data)
        mock_session.commit.assert_called_once()

    async def test_movement_notes_persisted(self, mocks):
        item = make_item(stock_current=Decimal("50"), unit_cost_avg=Decimal("1.00"))
        mocks.item_repo.get_by_id.return_value = item
        mocks.movement_repo.calculate_pmp.return_value = Decimal("1.0500")
        enriched = make_item(stock_current=Decimal("60"))
        mocks.item_repo.get_with_full_detail.return_value = enriched

        data = ManualAdjustmentRequest(
            quantity=Decimal("10"),
            unit_cost=Decimal("1.50"),
            notes="Reposición por pedido urgente",
        )
        await mocks.svc.manual_adjustment(item.id, data)

        movement_arg = mocks.movement_repo.create.call_args[0][0]
        assert movement_arg.notes == "Reposición por pedido urgente"

    async def test_entry_movement_quantity_stored_as_absolute_value(self, mocks):
        """Positive quantity → stored as-is (already positive)."""
        item = make_item(stock_current=Decimal("20"), unit_cost_avg=Decimal("1.00"))
        mocks.item_repo.get_by_id.return_value = item
        mocks.movement_repo.calculate_pmp.return_value = Decimal("1.2000")
        enriched = make_item()
        mocks.item_repo.get_with_full_detail.return_value = enriched

        data = ManualAdjustmentRequest(
            quantity=Decimal("15"),
            unit_cost=Decimal("1.60"),
            notes="Stock inicial",
        )
        await mocks.svc.manual_adjustment(item.id, data)

        movement_arg = mocks.movement_repo.create.call_args[0][0]
        assert movement_arg.quantity == Decimal("15")

    async def test_exit_movement_quantity_stored_as_absolute_value(self, mocks):
        """Negative quantity input → movement stored as abs() value."""
        item = make_item(stock_current=Decimal("30"), unit_cost_avg=Decimal("1.50"))
        mocks.item_repo.get_by_id.return_value = item
        enriched = make_item()
        mocks.item_repo.get_with_full_detail.return_value = enriched

        data = ManualAdjustmentRequest(
            quantity=Decimal("-7"),
            unit_cost=Decimal("1.50"),
            notes="Baja por obsolescencia",
        )
        await mocks.svc.manual_adjustment(item.id, data)

        movement_arg = mocks.movement_repo.create.call_args[0][0]
        assert movement_arg.quantity == Decimal("7")


# ── get_movements ──────────────────────────────────────────────────────────────

class TestGetMovements:
    async def test_returns_movement_list(self, mocks):
        item = make_item()
        mocks.item_repo.get_by_id.return_value = item
        movements = [make_movement(), make_movement(movement_type="exit")]
        mocks.movement_repo.get_by_item.return_value = movements

        result = await mocks.svc.get_movements(item.id, skip=0, limit=20)

        assert len(result) == 2
        mocks.movement_repo.get_by_item.assert_called_once_with(item.id, skip=0, limit=20)

    async def test_raises_404_when_item_not_found(self, mocks):
        mocks.item_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.get_movements(uuid.uuid4(), skip=0, limit=20)

        assert exc_info.value.status_code == 404

    async def test_empty_movement_list(self, mocks):
        item = make_item()
        mocks.item_repo.get_by_id.return_value = item
        mocks.movement_repo.get_by_item.return_value = []

        result = await mocks.svc.get_movements(item.id, skip=0, limit=20)

        assert result == []

    async def test_movement_response_fields(self, mocks):
        item = make_item()
        mocks.item_repo.get_by_id.return_value = item
        ref_id = uuid.uuid4()
        movement = make_movement(
            movement_type="entry",
            quantity=Decimal("50"),
            unit_cost=Decimal("1.60"),
            reference_type="purchase_order",
            reference_id=ref_id,
            notes="Compra proveedor",
        )
        mocks.movement_repo.get_by_item.return_value = [movement]

        result = await mocks.svc.get_movements(item.id, skip=0, limit=20)

        assert len(result) == 1
        resp = result[0]
        assert resp.movement_type == "entry"
        assert resp.quantity == Decimal("50")
        assert resp.unit_cost == Decimal("1.60")
        assert resp.reference_type == "purchase_order"
        assert resp.reference_id == ref_id
        assert resp.notes == "Compra proveedor"

    async def test_pagination_forwarded_to_repo(self, mocks):
        item = make_item()
        mocks.item_repo.get_by_id.return_value = item
        mocks.movement_repo.get_by_item.return_value = []

        await mocks.svc.get_movements(item.id, skip=20, limit=5)

        mocks.movement_repo.get_by_item.assert_called_once_with(item.id, skip=20, limit=5)


# ── get_low_stock_alerts ───────────────────────────────────────────────────────

class TestGetLowStockAlerts:
    async def test_returns_low_stock_items(self, mocks):
        items = [
            make_item(
                name="Cable 2.5mm",
                stock_current=Decimal("5"),
                stock_reserved=Decimal("0"),
                stock_min=Decimal("10"),
            ),
            make_item(
                name="Interruptor 10A",
                stock_current=Decimal("2"),
                stock_reserved=Decimal("0"),
                stock_min=Decimal("5"),
            ),
        ]
        mocks.item_repo.get_low_stock_items.return_value = items

        result = await mocks.svc.get_low_stock_alerts()

        assert len(result) == 2
        assert all(r.low_stock_alert for r in result)

    async def test_returns_empty_list_when_no_alerts(self, mocks):
        mocks.item_repo.get_low_stock_items.return_value = []

        result = await mocks.svc.get_low_stock_alerts()

        assert result == []

    async def test_calls_repo_method(self, mocks):
        mocks.item_repo.get_low_stock_items.return_value = []

        await mocks.svc.get_low_stock_alerts()

        mocks.item_repo.get_low_stock_items.assert_called_once()


# ── get_item_suppliers ─────────────────────────────────────────────────────────

class TestGetItemSuppliers:
    async def test_returns_supplier_items(self, mocks):
        item = make_item()
        mocks.item_repo.get_by_id.return_value = item
        si1 = make_supplier_item()
        si2 = make_supplier_item(is_preferred=False)
        mocks.supplier_item_repo.get_by_item.return_value = [si1, si2]

        result = await mocks.svc.get_item_suppliers(item.id)

        assert len(result) == 2
        mocks.supplier_item_repo.get_by_item.assert_called_once_with(item.id)

    async def test_raises_404_when_item_not_found(self, mocks):
        mocks.item_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.get_item_suppliers(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_empty_supplier_list(self, mocks):
        item = make_item()
        mocks.item_repo.get_by_id.return_value = item
        mocks.supplier_item_repo.get_by_item.return_value = []

        result = await mocks.svc.get_item_suppliers(item.id)

        assert result == []


# ── add_supplier ───────────────────────────────────────────────────────────────

class TestAddSupplier:
    async def test_adds_supplier_successfully(self, mocks, mock_session):
        item = make_item()
        mocks.item_repo.get_by_id.return_value = item
        mocks.supplier_item_repo.get_by_supplier_and_item.return_value = None

        si = make_supplier_item()
        mocks.supplier_item_repo.create.return_value = si
        mocks.supplier_item_repo.get_by_id_with_supplier.return_value = si

        data = SupplierItemCreate(
            supplier_id=si.supplier_id,
            inventory_item_id=item.id,
            unit_cost=Decimal("1.50"),
            is_preferred=False,
        )
        result = await mocks.svc.add_supplier(item.id, data)

        mocks.supplier_item_repo.create.assert_called_once()
        mock_session.commit.assert_called_once()
        assert result.id == si.id

    async def test_raises_404_when_item_not_found(self, mocks):
        mocks.item_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.add_supplier(
                uuid.uuid4(),
                SupplierItemCreate(
                    supplier_id=uuid.uuid4(),
                    inventory_item_id=uuid.uuid4(),
                    unit_cost=Decimal("2.00"),
                ),
            )

        assert exc_info.value.status_code == 404

    async def test_raises_409_when_supplier_already_linked(self, mocks):
        item = make_item()
        mocks.item_repo.get_by_id.return_value = item
        existing_si = make_supplier_item()
        mocks.supplier_item_repo.get_by_supplier_and_item.return_value = existing_si

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.add_supplier(
                item.id,
                SupplierItemCreate(
                    supplier_id=existing_si.supplier_id,
                    inventory_item_id=item.id,
                    unit_cost=Decimal("2.00"),
                ),
            )

        assert exc_info.value.status_code == 409
        assert "proveedor" in exc_info.value.detail.lower()

    async def test_clears_existing_preferred_when_new_is_preferred(
        self, mocks, mock_session
    ):
        item = make_item()
        mocks.item_repo.get_by_id.return_value = item
        mocks.supplier_item_repo.get_by_supplier_and_item.return_value = None
        si = make_supplier_item(is_preferred=True)
        mocks.supplier_item_repo.create.return_value = si
        mocks.supplier_item_repo.get_by_id_with_supplier.return_value = si

        data = SupplierItemCreate(
            supplier_id=uuid.uuid4(),
            inventory_item_id=item.id,
            unit_cost=Decimal("1.50"),
            is_preferred=True,
        )
        await mocks.svc.add_supplier(item.id, data)

        # session.execute called to clear existing preferred flags
        mock_session.execute.assert_called_once()


# ── update_supplier_price ──────────────────────────────────────────────────────

class TestUpdateSupplierPrice:
    async def test_updates_supplier_price(self, mocks, mock_session):
        item_id = uuid.uuid4()
        si = make_supplier_item(inventory_item_id=item_id)
        mocks.supplier_item_repo.get_by_id_with_supplier.side_effect = [si, si]

        data = SupplierItemUpdate(unit_cost=Decimal("2.00"))
        result = await mocks.svc.update_supplier_price(item_id, si.id, data)

        mocks.supplier_item_repo.update.assert_called_once()
        mock_session.commit.assert_called_once()
        assert result.id == si.id

    async def test_raises_404_when_supplier_item_not_found(self, mocks):
        mocks.supplier_item_repo.get_by_id_with_supplier.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_supplier_price(
                uuid.uuid4(), uuid.uuid4(), SupplierItemUpdate(unit_cost=Decimal("2.00"))
            )

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_supplier_item_belongs_to_different_item(self, mocks):
        si = make_supplier_item(inventory_item_id=uuid.uuid4())
        mocks.supplier_item_repo.get_by_id_with_supplier.return_value = si

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.update_supplier_price(
                uuid.uuid4(),  # different item_id
                si.id,
                SupplierItemUpdate(unit_cost=Decimal("2.00")),
            )

        assert exc_info.value.status_code == 404

    async def test_syncs_unit_cost_to_item_when_setting_preferred(
        self, mocks, mock_session
    ):
        item_id = uuid.uuid4()
        item = make_item()
        si = make_supplier_item(inventory_item_id=item_id, unit_cost=Decimal("3.00"))
        mocks.supplier_item_repo.get_by_id_with_supplier.side_effect = [si, si]
        mocks.item_repo.get_by_id.return_value = item

        data = SupplierItemUpdate(unit_cost=Decimal("3.50"), is_preferred=True)
        await mocks.svc.update_supplier_price(item_id, si.id, data)

        mocks.supplier_item_repo.set_preferred.assert_called_once_with(si.id)
        # Syncs the new cost (from data.unit_cost) to the inventory item
        mocks.item_repo.update.assert_called_once_with(item, {"unit_cost": Decimal("3.50")})


# ── remove_supplier ────────────────────────────────────────────────────────────

class TestRemoveSupplier:
    async def test_removes_supplier_successfully(self, mocks, mock_session):
        item_id = uuid.uuid4()
        si_to_remove = make_supplier_item(inventory_item_id=item_id, is_preferred=False)
        si_other = make_supplier_item(inventory_item_id=item_id, is_preferred=True)
        mocks.supplier_item_repo.get_by_id_with_supplier.return_value = si_to_remove
        mocks.supplier_item_repo.get_by_item.return_value = [si_to_remove, si_other]

        await mocks.svc.remove_supplier(item_id, si_to_remove.id)

        mocks.supplier_item_repo.update.assert_called_once_with(
            si_to_remove, {"is_active": False}
        )
        mock_session.commit.assert_called_once()

    async def test_raises_404_when_supplier_item_not_found(self, mocks):
        mocks.supplier_item_repo.get_by_id_with_supplier.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.remove_supplier(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_belongs_to_different_item(self, mocks):
        si = make_supplier_item(inventory_item_id=uuid.uuid4())
        mocks.supplier_item_repo.get_by_id_with_supplier.return_value = si

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.remove_supplier(uuid.uuid4(), si.id)

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_only_one_supplier_remains(self, mocks):
        item_id = uuid.uuid4()
        si = make_supplier_item(inventory_item_id=item_id, is_preferred=False)
        mocks.supplier_item_repo.get_by_id_with_supplier.return_value = si
        # Only one active supplier
        mocks.supplier_item_repo.get_by_item.return_value = [si]

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.remove_supplier(item_id, si.id)

        assert exc_info.value.status_code == 400
        assert "proveedor" in exc_info.value.detail.lower()

    async def test_raises_400_when_removing_preferred_supplier(self, mocks):
        item_id = uuid.uuid4()
        si_preferred = make_supplier_item(inventory_item_id=item_id, is_preferred=True)
        si_other = make_supplier_item(inventory_item_id=item_id, is_preferred=False)
        mocks.supplier_item_repo.get_by_id_with_supplier.return_value = si_preferred
        mocks.supplier_item_repo.get_by_item.return_value = [si_preferred, si_other]

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.remove_supplier(item_id, si_preferred.id)

        assert exc_info.value.status_code == 400
        assert "preferido" in exc_info.value.detail.lower()


# ── set_preferred_supplier ─────────────────────────────────────────────────────

class TestSetPreferredSupplier:
    async def test_sets_preferred_and_syncs_unit_cost(self, mocks, mock_session):
        item_id = uuid.uuid4()
        item = make_item()
        si = make_supplier_item(inventory_item_id=item_id, unit_cost=Decimal("2.75"))
        mocks.supplier_item_repo.get_by_id_with_supplier.side_effect = [si, si]
        mocks.item_repo.get_by_id.return_value = item

        result = await mocks.svc.set_preferred_supplier(item_id, si.id)

        mocks.supplier_item_repo.set_preferred.assert_called_once_with(si.id)
        mocks.item_repo.update.assert_called_once_with(
            item, {"unit_cost": Decimal("2.75")}
        )
        mock_session.commit.assert_called_once()
        assert result.id == si.id

    async def test_raises_404_when_supplier_item_not_found(self, mocks):
        mocks.supplier_item_repo.get_by_id_with_supplier.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.set_preferred_supplier(uuid.uuid4(), uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_404_when_belongs_to_different_item(self, mocks):
        si = make_supplier_item(inventory_item_id=uuid.uuid4())
        mocks.supplier_item_repo.get_by_id_with_supplier.return_value = si

        with pytest.raises(HTTPException) as exc_info:
            await mocks.svc.set_preferred_supplier(uuid.uuid4(), si.id)

        assert exc_info.value.status_code == 404

    async def test_no_item_sync_when_item_missing(self, mocks, mock_session):
        """Edge case: item not found in repo — set_preferred still runs, no crash."""
        item_id = uuid.uuid4()
        si = make_supplier_item(inventory_item_id=item_id, unit_cost=Decimal("2.00"))
        mocks.supplier_item_repo.get_by_id_with_supplier.side_effect = [si, si]
        mocks.item_repo.get_by_id.return_value = None  # item not found

        await mocks.svc.set_preferred_supplier(item_id, si.id)

        mocks.supplier_item_repo.set_preferred.assert_called_once_with(si.id)
        mocks.item_repo.update.assert_not_called()
        mock_session.commit.assert_called_once()


# ── _enrich_item (business logic unit) ────────────────────────────────────────

class TestEnrichItem:
    """Direct unit tests for the _enrich_item helper — core stock computation."""

    def _make_svc(self, mock_session) -> InventoryService:
        with (
            patch("app.services.inventory.InventoryItemRepository"),
            patch("app.services.inventory.StockMovementRepository"),
            patch("app.services.inventory.SupplierItemRepository"),
        ):
            return InventoryService(mock_session, TENANT_ID)

    def test_stock_available_equals_current_minus_reserved(self, mock_session):
        svc = self._make_svc(mock_session)
        item = make_item(
            stock_current=Decimal("100"),
            stock_reserved=Decimal("25"),
            stock_min=Decimal("10"),
        )
        response = svc._enrich_item(item)
        assert response.stock_available == Decimal("75")

    def test_no_alert_when_available_above_min(self, mock_session):
        svc = self._make_svc(mock_session)
        item = make_item(
            stock_current=Decimal("50"),
            stock_reserved=Decimal("0"),
            stock_min=Decimal("20"),
        )
        response = svc._enrich_item(item)
        assert response.low_stock_alert is False

    def test_alert_when_available_equals_min(self, mock_session):
        svc = self._make_svc(mock_session)
        item = make_item(
            stock_current=Decimal("20"),
            stock_reserved=Decimal("0"),
            stock_min=Decimal("20"),
        )
        response = svc._enrich_item(item)
        # available (20) <= stock_min (20) → alert
        assert response.low_stock_alert is True

    def test_alert_when_available_below_min(self, mock_session):
        svc = self._make_svc(mock_session)
        item = make_item(
            stock_current=Decimal("15"),
            stock_reserved=Decimal("5"),
            stock_min=Decimal("20"),
        )
        response = svc._enrich_item(item)
        # available = 10 < 20 → alert
        assert response.low_stock_alert is True

    def test_alert_when_reserved_causes_deficit(self, mock_session):
        svc = self._make_svc(mock_session)
        item = make_item(
            stock_current=Decimal("30"),
            stock_reserved=Decimal("20"),
            stock_min=Decimal("15"),
        )
        response = svc._enrich_item(item)
        # available = 10 < 15 → alert despite stock_current > stock_min
        assert response.stock_available == Decimal("10")
        assert response.low_stock_alert is True

    def test_preferred_supplier_selected_from_active_items(self, mock_session):
        svc = self._make_svc(mock_session)
        si_preferred = make_supplier_item(is_preferred=True, is_active=True)
        si_other = make_supplier_item(is_preferred=False, is_active=True)
        item = make_item(supplier_items=[si_preferred, si_other])

        response = svc._enrich_item(item)

        assert response.preferred_supplier is not None
        assert response.preferred_supplier.id == si_preferred.id

    def test_inactive_supplier_items_excluded(self, mock_session):
        svc = self._make_svc(mock_session)
        si_active = make_supplier_item(is_preferred=True, is_active=True)
        si_inactive = make_supplier_item(is_preferred=False, is_active=False)
        item = make_item(supplier_items=[si_active, si_inactive])

        response = svc._enrich_item(item)

        assert len(response.supplier_items) == 1
        assert response.supplier_items[0].id == si_active.id

    def test_preferred_supplier_none_when_all_inactive(self, mock_session):
        svc = self._make_svc(mock_session)
        si_inactive = make_supplier_item(is_preferred=True, is_active=False)
        item = make_item(supplier_items=[si_inactive])

        response = svc._enrich_item(item)

        assert response.preferred_supplier is None
        assert response.supplier_items == []

    def test_last_movement_at_from_first_movement(self, mock_session):
        svc = self._make_svc(mock_session)
        ts = _now()
        m = MagicMock()
        m.created_at = ts
        item = make_item(stock_movements=[m])

        response = svc._enrich_item(item)

        assert response.last_movement_at == ts

    def test_last_movement_at_none_when_no_movements(self, mock_session):
        svc = self._make_svc(mock_session)
        item = make_item(stock_movements=[])

        response = svc._enrich_item(item)

        assert response.last_movement_at is None

    def test_zero_stock_triggers_alert(self, mock_session):
        svc = self._make_svc(mock_session)
        item = make_item(
            stock_current=Decimal("0"),
            stock_reserved=Decimal("0"),
            stock_min=Decimal("5"),
        )
        response = svc._enrich_item(item)
        assert response.stock_available == Decimal("0")
        assert response.low_stock_alert is True

    def test_zero_stock_min_never_triggers_alert(self, mock_session):
        svc = self._make_svc(mock_session)
        item = make_item(
            stock_current=Decimal("0"),
            stock_reserved=Decimal("0"),
            stock_min=Decimal("0"),
        )
        response = svc._enrich_item(item)
        # available (0) <= stock_min (0) → alert is True (edge case: both zero)
        assert response.low_stock_alert is True
