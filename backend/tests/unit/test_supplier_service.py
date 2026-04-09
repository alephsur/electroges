"""
Unit tests for SupplierService and PurchaseOrderService.

All repositories and the DB session are mocked — no database required.
Each public service method gets its own test class, covering:
  - Happy path
  - 404 / 409 / 400 error cases
  - Delegation and call arguments to repos
  - Commit / flush behaviour
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import NamedTuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.schemas.supplier_item import SupplierItemCreate, SupplierItemUpdate
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderLineCreate,
    PurchaseOrderUpdate,
)
from app.services.supplier import SupplierService
from app.services.purchase_order import PurchaseOrderService

TENANT_ID = uuid.uuid4()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_supplier(**kwargs) -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.tenant_id = TENANT_ID
    s.name = "Distribuciones García"
    s.tax_id = "B12345678"
    s.email = "garcia@proveedores.es"
    s.phone = "912345678"
    s.address = "Calle Mayor 1"
    s.contact_person = "Carlos García"
    s.payment_terms = "30 días"
    s.notes = None
    s.is_active = True
    s.created_at = _now()
    s.updated_at = _now()
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


def make_supplier_item(**kwargs) -> MagicMock:
    si = MagicMock()
    si.id = uuid.uuid4()
    si.supplier_id = uuid.uuid4()
    si.inventory_item_id = uuid.uuid4()
    si.supplier_ref = "REF-001"
    si.unit_cost = Decimal("1.50")
    si.last_purchase_cost = None
    si.last_purchase_date = None
    si.lead_time_days = 5
    si.is_preferred = False
    si.is_active = True
    si.created_at = _now()
    si.updated_at = _now()
    # Provide a related supplier mock (needed by _build_supplier_item_response)
    si.supplier = MagicMock()
    si.supplier.name = "Distribuciones García"
    for k, v in kwargs.items():
        setattr(si, k, v)
    return si


def make_inventory_item(**kwargs) -> MagicMock:
    item = MagicMock()
    item.id = uuid.uuid4()
    item.tenant_id = TENANT_ID
    item.name = "Cable 2.5mm²"
    item.description = None
    item.unit = "m"
    item.unit_cost = Decimal("1.00")
    item.unit_cost_avg = Decimal("0.00")
    item.unit_price = Decimal("2.00")
    item.stock_current = Decimal("100")
    item.stock_min = Decimal("10")
    item.supplier_id = None
    item.is_active = True
    item.created_at = _now()
    item.updated_at = _now()
    item.supplier_items = []
    for k, v in kwargs.items():
        setattr(item, k, v)
    return item


def make_purchase_order(**kwargs) -> MagicMock:
    o = MagicMock()
    o.id = uuid.uuid4()
    o.tenant_id = TENANT_ID
    o.supplier_id = uuid.uuid4()
    o.order_number = "PED-2026-0001"
    o.status = "pending"
    o.order_date = date(2026, 1, 10)
    o.expected_date = date(2026, 1, 17)
    o.received_date = None
    o.notes = None
    o.lines = []
    o.total = Decimal("0.00")
    o.created_at = _now()
    o.updated_at = _now()
    for k, v in kwargs.items():
        setattr(o, k, v)
    return o


def make_order_line(inventory_item_id=None, **kwargs) -> MagicMock:
    line = MagicMock()
    line.id = uuid.uuid4()
    line.purchase_order_id = uuid.uuid4()
    line.inventory_item_id = inventory_item_id or uuid.uuid4()
    line.description = None
    line.quantity = Decimal("10")
    line.unit_cost = Decimal("2.50")
    line.subtotal = Decimal("25.00")
    line.supplier_item_id = None
    line.inventory_item = None
    line.created_at = _now()
    line.updated_at = _now()
    for k, v in kwargs.items():
        setattr(line, k, v)
    return line


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


# ── SupplierService fixtures ───────────────────────────────────────────────────


class _SupplierMocks(NamedTuple):
    svc: SupplierService
    repo: AsyncMock


@pytest.fixture
def supplier_mocks(mock_session) -> _SupplierMocks:
    repo = AsyncMock()
    with patch("app.services.supplier.SupplierRepository", return_value=repo):
        svc = SupplierService(mock_session, TENANT_ID)
        yield _SupplierMocks(svc, repo)


# ── PurchaseOrderService fixtures ──────────────────────────────────────────────


class _POmocks(NamedTuple):
    svc: PurchaseOrderService
    repo: AsyncMock
    item_repo: AsyncMock
    movement_repo: AsyncMock
    supplier_item_repo: AsyncMock


@pytest.fixture
def po_mocks(mock_session) -> _POmocks:
    repo = AsyncMock()
    item_repo = AsyncMock()
    movement_repo = AsyncMock()
    supplier_item_repo = AsyncMock()

    with (
        patch("app.services.purchase_order.PurchaseOrderRepository", return_value=repo),
        patch("app.services.purchase_order.InventoryItemRepository", return_value=item_repo),
        patch("app.services.purchase_order.StockMovementRepository", return_value=movement_repo),
        patch("app.services.purchase_order.SupplierItemRepository", return_value=supplier_item_repo),
    ):
        svc = PurchaseOrderService(mock_session, TENANT_ID)
        yield _POmocks(svc, repo, item_repo, movement_repo, supplier_item_repo)


# ══════════════════════════════════════════════════════════════════════════════
# SupplierService tests
# ══════════════════════════════════════════════════════════════════════════════


# ── list_suppliers ─────────────────────────────────────────────────────────────


class TestListSuppliers:
    async def test_returns_paginated_response(self, supplier_mocks):
        svc, repo = supplier_mocks
        repo.search.return_value = ([make_supplier(), make_supplier()], 2)

        result = await svc.list_suppliers(skip=0, limit=50)

        assert result.total == 2
        assert len(result.items) == 2
        assert result.skip == 0
        assert result.limit == 50

    async def test_passes_filters_to_repo(self, supplier_mocks):
        svc, repo = supplier_mocks
        repo.search.return_value = ([], 0)

        await svc.list_suppliers(q="garcía", is_active=True, skip=10, limit=20)

        repo.search.assert_called_once_with(query="garcía", is_active=True, skip=10, limit=20)

    async def test_returns_empty_list(self, supplier_mocks):
        svc, repo = supplier_mocks
        repo.search.return_value = ([], 0)

        result = await svc.list_suppliers()

        assert result.total == 0
        assert result.items == []

    async def test_inactive_filter_passed_through(self, supplier_mocks):
        svc, repo = supplier_mocks
        repo.search.return_value = ([make_supplier(is_active=False)], 1)

        result = await svc.list_suppliers(is_active=False)

        repo.search.assert_called_once_with(query=None, is_active=False, skip=0, limit=100)
        assert result.total == 1

    async def test_default_is_active_true(self, supplier_mocks):
        svc, repo = supplier_mocks
        repo.search.return_value = ([], 0)

        await svc.list_suppliers()

        _, kwargs = repo.search.call_args
        assert kwargs.get("is_active", True) is True


# ── get_supplier ───────────────────────────────────────────────────────────────


class TestGetSupplier:
    async def test_returns_response_when_found(self, supplier_mocks):
        svc, repo = supplier_mocks
        supplier = make_supplier(name="Eléctricos Norte")
        repo.get_by_id.return_value = supplier

        result = await svc.get_supplier(supplier.id)

        assert result.name == "Eléctricos Norte"
        assert result.id == supplier.id

    async def test_raises_404_when_not_found(self, supplier_mocks):
        svc, repo = supplier_mocks
        repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_supplier(uuid.uuid4())

        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()

    async def test_delegates_correct_id_to_repo(self, supplier_mocks):
        svc, repo = supplier_mocks
        supplier_id = uuid.uuid4()
        repo.get_by_id.return_value = make_supplier(id=supplier_id)

        await svc.get_supplier(supplier_id)

        repo.get_by_id.assert_called_once_with(supplier_id)


# ── create_supplier ────────────────────────────────────────────────────────────


class TestCreateSupplier:
    async def test_creates_and_returns_supplier(self, supplier_mocks):
        svc, repo = supplier_mocks
        created = make_supplier(name="Nuevo Proveedor")
        repo.get_by_tax_id.return_value = None
        repo.create.return_value = created

        data = SupplierCreate(name="Nuevo Proveedor", tax_id="C99999999")
        result = await svc.create_supplier(data)

        assert result.name == "Nuevo Proveedor"
        repo.create.assert_called_once()

    async def test_commits_after_create(self, supplier_mocks, mock_session):
        svc, repo = supplier_mocks
        repo.get_by_tax_id.return_value = None
        repo.create.return_value = make_supplier()

        await svc.create_supplier(SupplierCreate(name="X"))

        mock_session.commit.assert_called_once()

    async def test_raises_409_on_duplicate_tax_id(self, supplier_mocks):
        svc, repo = supplier_mocks
        repo.get_by_tax_id.return_value = make_supplier(tax_id="B11111111")

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_supplier(SupplierCreate(name="Duplicado", tax_id="B11111111"))

        assert exc_info.value.status_code == 409
        assert "B11111111" in exc_info.value.detail

    async def test_skips_tax_id_check_when_none(self, supplier_mocks):
        svc, repo = supplier_mocks
        repo.create.return_value = make_supplier(tax_id=None)

        await svc.create_supplier(SupplierCreate(name="Sin CIF"))

        repo.get_by_tax_id.assert_not_called()

    async def test_creates_with_correct_tenant(self, supplier_mocks, mock_session):
        svc, repo = supplier_mocks
        # The service builds a real Supplier(...) and passes it to repo.create.
        # The real model has no id/timestamps until the DB flushes, so we must
        # return our pre-built mock — not the raw model — to satisfy model_validate.
        pre_built = make_supplier(tenant_id=TENANT_ID)
        captured_supplier = None

        async def capture(s):
            nonlocal captured_supplier
            captured_supplier = s
            return pre_built  # return mock with all required fields set

        repo.create.side_effect = capture

        await svc.create_supplier(SupplierCreate(name="X"))

        assert captured_supplier.tenant_id == TENANT_ID


# ── update_supplier ────────────────────────────────────────────────────────────


class TestUpdateSupplier:
    async def test_updates_name(self, supplier_mocks):
        svc, repo = supplier_mocks
        original = make_supplier(name="Viejo Nombre")
        updated = make_supplier(name="Nuevo Nombre")
        repo.get_by_id.return_value = original
        repo.update.return_value = updated

        result = await svc.update_supplier(original.id, SupplierUpdate(name="Nuevo Nombre"))

        assert result.name == "Nuevo Nombre"

    async def test_raises_404_when_not_found(self, supplier_mocks):
        svc, repo = supplier_mocks
        repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.update_supplier(uuid.uuid4(), SupplierUpdate(name="X"))

        assert exc_info.value.status_code == 404

    async def test_raises_409_on_tax_id_conflict(self, supplier_mocks):
        svc, repo = supplier_mocks
        existing_supplier = make_supplier(tax_id="A00000001")
        conflicting = make_supplier(tax_id="A00000002", id=uuid.uuid4())
        repo.get_by_id.return_value = existing_supplier
        repo.get_by_tax_id.return_value = conflicting

        with pytest.raises(HTTPException) as exc_info:
            await svc.update_supplier(
                existing_supplier.id, SupplierUpdate(tax_id="A00000002")
            )

        assert exc_info.value.status_code == 409

    async def test_no_tax_id_check_when_same_value(self, supplier_mocks):
        """If the new tax_id is identical to the existing one, no uniqueness check."""
        svc, repo = supplier_mocks
        supplier = make_supplier(tax_id="A00000001")
        repo.get_by_id.return_value = supplier
        repo.update.return_value = supplier

        await svc.update_supplier(supplier.id, SupplierUpdate(tax_id="A00000001"))

        repo.get_by_tax_id.assert_not_called()

    async def test_no_tax_id_check_when_field_not_set(self, supplier_mocks):
        svc, repo = supplier_mocks
        supplier = make_supplier()
        repo.get_by_id.return_value = supplier
        repo.update.return_value = supplier

        await svc.update_supplier(supplier.id, SupplierUpdate(notes="nota"))

        repo.get_by_tax_id.assert_not_called()

    async def test_commits_after_update(self, supplier_mocks, mock_session):
        svc, repo = supplier_mocks
        supplier = make_supplier()
        repo.get_by_id.return_value = supplier
        repo.update.return_value = supplier

        await svc.update_supplier(supplier.id, SupplierUpdate(name="Y"))

        mock_session.commit.assert_called_once()

    async def test_delegates_only_set_fields(self, supplier_mocks):
        svc, repo = supplier_mocks
        supplier = make_supplier()
        repo.get_by_id.return_value = supplier
        repo.update.return_value = supplier

        await svc.update_supplier(supplier.id, SupplierUpdate(notes="new note"))

        _, call_args = repo.update.call_args
        # Second positional arg is the update dict — check via args
        update_dict = repo.update.call_args.args[1]
        assert "notes" in update_dict
        assert "name" not in update_dict


# ── deactivate_supplier ────────────────────────────────────────────────────────


class TestDeactivateSupplier:
    async def test_deactivates_supplier(self, supplier_mocks):
        svc, repo = supplier_mocks
        supplier = make_supplier(is_active=True)
        repo.get_by_id.return_value = supplier

        await svc.deactivate_supplier(supplier.id)

        repo.update.assert_called_once_with(supplier, {"is_active": False})

    async def test_raises_404_when_not_found(self, supplier_mocks):
        svc, repo = supplier_mocks
        repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.deactivate_supplier(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_commits_after_deactivation(self, supplier_mocks, mock_session):
        svc, repo = supplier_mocks
        supplier = make_supplier()
        repo.get_by_id.return_value = supplier

        await svc.deactivate_supplier(supplier.id)

        mock_session.commit.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# PurchaseOrderService tests
# ══════════════════════════════════════════════════════════════════════════════


# ── list_by_supplier ───────────────────────────────────────────────────────────


class TestListBySupplier:
    async def test_returns_paginated_list(self, po_mocks):
        svc, repo, *_ = po_mocks
        order = make_purchase_order()
        repo.get_by_supplier.return_value = ([(order, Decimal("50.00"))], 1)

        result = await svc.list_by_supplier(order.supplier_id)

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].total == Decimal("50.00")

    async def test_empty_list(self, po_mocks):
        svc, repo, *_ = po_mocks
        repo.get_by_supplier.return_value = ([], 0)

        result = await svc.list_by_supplier(uuid.uuid4())

        assert result.total == 0
        assert result.items == []

    async def test_passes_status_filter(self, po_mocks):
        svc, repo, *_ = po_mocks
        supplier_id = uuid.uuid4()
        repo.get_by_supplier.return_value = ([], 0)

        await svc.list_by_supplier(supplier_id, status_filter="pending", skip=5, limit=25)

        repo.get_by_supplier.assert_called_once_with(
            supplier_id, status="pending", skip=5, limit=25
        )

    async def test_sets_total_on_summary_from_repo(self, po_mocks):
        svc, repo, *_ = po_mocks
        order = make_purchase_order(status="received")
        repo.get_by_supplier.return_value = ([(order, Decimal("123.45"))], 1)

        result = await svc.list_by_supplier(order.supplier_id)

        assert result.items[0].total == Decimal("123.45")


# ── get_order ──────────────────────────────────────────────────────────────────


class TestGetOrder:
    async def test_returns_order_when_found(self, po_mocks):
        svc, repo, *_ = po_mocks
        order = make_purchase_order()
        repo.get_with_lines.return_value = order

        result = await svc.get_order(order.id)

        assert result.id == order.id
        assert result.order_number == order.order_number

    async def test_raises_404_when_not_found(self, po_mocks):
        svc, repo, *_ = po_mocks
        repo.get_with_lines.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_order(uuid.uuid4())

        assert exc_info.value.status_code == 404
        assert "Pedido no encontrado" in exc_info.value.detail


# ── create_order ───────────────────────────────────────────────────────────────


class TestCreateOrder:
    def _make_create_data(self, **kwargs) -> PurchaseOrderCreate:
        defaults = dict(
            supplier_id=uuid.uuid4(),
            order_date=date(2026, 1, 10),
            lines=[
                PurchaseOrderLineCreate(
                    description="Cable",
                    quantity=Decimal("5"),
                    unit_cost=Decimal("2.00"),
                ),
            ],
        )
        defaults.update(kwargs)
        return PurchaseOrderCreate(**defaults)

    async def test_creates_and_returns_order(self, po_mocks, mock_session):
        svc, repo, *_ = po_mocks
        order = make_purchase_order()
        repo.get_next_order_number.return_value = "PED-2026-0001"
        repo.create.return_value = order
        repo.get_with_lines.return_value = order

        result = await svc.create_order(self._make_create_data())

        assert result.order_number == "PED-2026-0001"

    async def test_commits_after_create(self, po_mocks, mock_session):
        svc, repo, *_ = po_mocks
        order = make_purchase_order()
        repo.get_next_order_number.return_value = "PED-2026-0001"
        repo.create.return_value = order
        repo.get_with_lines.return_value = order

        await svc.create_order(self._make_create_data())

        mock_session.commit.assert_called_once()

    async def test_flushes_before_final_fetch(self, po_mocks, mock_session):
        svc, repo, *_ = po_mocks
        order = make_purchase_order()
        repo.get_next_order_number.return_value = "PED-2026-0001"
        repo.create.return_value = order
        repo.get_with_lines.return_value = order

        await svc.create_order(self._make_create_data())

        mock_session.flush.assert_called_once()

    async def test_creates_order_line_per_input_line(self, po_mocks, mock_session):
        svc, repo, *_ = po_mocks
        order = make_purchase_order()
        repo.get_next_order_number.return_value = "PED-2026-0001"
        repo.create.return_value = order
        repo.get_with_lines.return_value = order

        data = self._make_create_data()
        data = PurchaseOrderCreate(
            supplier_id=uuid.uuid4(),
            order_date=date.today(),
            lines=[
                PurchaseOrderLineCreate(description="A", quantity=Decimal("1"), unit_cost=Decimal("1")),
                PurchaseOrderLineCreate(description="B", quantity=Decimal("2"), unit_cost=Decimal("2")),
            ],
        )

        await svc.create_order(data)

        # session.add called twice — once per line
        assert mock_session.add.call_count == 2

    async def test_subtotal_computed_correctly(self, po_mocks, mock_session):
        """subtotal = quantity * unit_cost, quantized to 4 decimal places."""
        svc, repo, *_ = po_mocks
        order = make_purchase_order()
        repo.get_next_order_number.return_value = "PED-2026-0001"
        repo.create.return_value = order
        repo.get_with_lines.return_value = order
        captured_lines = []

        def capture_add(obj):
            from app.models.purchase_order import PurchaseOrderLine
            if hasattr(obj, "subtotal"):
                captured_lines.append(obj)

        mock_session.add.side_effect = capture_add

        data = PurchaseOrderCreate(
            supplier_id=uuid.uuid4(),
            order_date=date.today(),
            lines=[
                PurchaseOrderLineCreate(
                    description="Item",
                    quantity=Decimal("3"),
                    unit_cost=Decimal("1.1111"),
                ),
            ],
        )

        await svc.create_order(data)

        assert len(captured_lines) == 1
        assert captured_lines[0].subtotal == Decimal("3.3333")


# ── update_order ───────────────────────────────────────────────────────────────


class TestUpdateOrder:
    async def test_updates_notes(self, po_mocks):
        svc, repo, *_ = po_mocks
        order = make_purchase_order(status="pending")
        updated_order = make_purchase_order(notes="Nueva nota")
        repo.get_by_id.return_value = order
        repo.update.return_value = order
        repo.get_with_lines.return_value = updated_order

        result = await svc.update_order(order.id, PurchaseOrderUpdate(notes="Nueva nota"))

        repo.update.assert_called_once()

    async def test_raises_404_when_not_found(self, po_mocks):
        svc, repo, *_ = po_mocks
        repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.update_order(uuid.uuid4(), PurchaseOrderUpdate(notes="X"))

        assert exc_info.value.status_code == 404

    async def test_raises_409_when_not_pending(self, po_mocks):
        svc, repo, *_ = po_mocks
        repo.get_by_id.return_value = make_purchase_order(status="received")

        with pytest.raises(HTTPException) as exc_info:
            await svc.update_order(uuid.uuid4(), PurchaseOrderUpdate(notes="X"))

        assert exc_info.value.status_code == 409
        assert "pending" in exc_info.value.detail

    async def test_raises_409_when_cancelled(self, po_mocks):
        svc, repo, *_ = po_mocks
        repo.get_by_id.return_value = make_purchase_order(status="cancelled")

        with pytest.raises(HTTPException) as exc_info:
            await svc.update_order(uuid.uuid4(), PurchaseOrderUpdate(notes="X"))

        assert exc_info.value.status_code == 409

    async def test_commits_after_update(self, po_mocks, mock_session):
        svc, repo, *_ = po_mocks
        order = make_purchase_order(status="pending")
        repo.get_by_id.return_value = order
        repo.update.return_value = order
        repo.get_with_lines.return_value = order

        await svc.update_order(order.id, PurchaseOrderUpdate(notes="nota"))

        mock_session.commit.assert_called_once()


# ── receive_order ──────────────────────────────────────────────────────────────


class TestReceiveOrder:
    async def test_raises_404_when_not_found(self, po_mocks):
        svc, repo, *_ = po_mocks
        repo.get_with_lines.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.receive_order(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_409_when_already_received(self, po_mocks):
        svc, repo, *_ = po_mocks
        repo.get_with_lines.return_value = make_purchase_order(status="received")

        with pytest.raises(HTTPException) as exc_info:
            await svc.receive_order(uuid.uuid4())

        assert exc_info.value.status_code == 409
        assert "pending" in exc_info.value.detail

    async def test_raises_409_when_cancelled(self, po_mocks):
        svc, repo, *_ = po_mocks
        repo.get_with_lines.return_value = make_purchase_order(status="cancelled")

        with pytest.raises(HTTPException) as exc_info:
            await svc.receive_order(uuid.uuid4())

        assert exc_info.value.status_code == 409

    async def test_creates_stock_movement_per_inventory_line(self, po_mocks, mock_session):
        svc, repo, item_repo, movement_repo, supplier_item_repo = po_mocks
        item_id = uuid.uuid4()
        line = make_order_line(inventory_item_id=item_id)
        order = make_purchase_order(status="pending", lines=[line])
        received_order = make_purchase_order(status="received", lines=[line])

        repo.get_with_lines.side_effect = [order, received_order]
        item_repo.get_by_id.return_value = make_inventory_item(id=item_id)
        movement_repo.create.return_value = MagicMock()
        movement_repo.calculate_pmp.return_value = Decimal("2.50")
        item_repo.update_stock_and_pmp.return_value = None
        supplier_item_repo.get_by_supplier_and_item.return_value = None
        repo.update.return_value = order

        await svc.receive_order(order.id)

        movement_repo.create.assert_called_once()

    async def test_updates_stock_and_pmp(self, po_mocks, mock_session):
        svc, repo, item_repo, movement_repo, supplier_item_repo = po_mocks
        item_id = uuid.uuid4()
        line = make_order_line(inventory_item_id=item_id, quantity=Decimal("10"), unit_cost=Decimal("3.00"))
        order = make_purchase_order(status="pending", lines=[line])
        received_order = make_purchase_order(status="received")

        repo.get_with_lines.side_effect = [order, received_order]
        item = make_inventory_item(id=item_id)
        item_repo.get_by_id.return_value = item
        movement_repo.create.return_value = MagicMock()
        new_pmp = Decimal("3.00")
        movement_repo.calculate_pmp.return_value = new_pmp
        supplier_item_repo.get_by_supplier_and_item.return_value = None
        repo.update.return_value = order

        await svc.receive_order(order.id)

        item_repo.update_stock_and_pmp.assert_called_once_with(item_id, line.quantity, new_pmp)

    async def test_skips_line_without_inventory_item(self, po_mocks, mock_session):
        """Lines with inventory_item_id=None (free-text lines) should be skipped."""
        svc, repo, item_repo, movement_repo, supplier_item_repo = po_mocks
        line = make_order_line(inventory_item_id=None)
        line.inventory_item_id = None  # explicitly None
        order = make_purchase_order(status="pending", lines=[line])
        received_order = make_purchase_order(status="received")

        repo.get_with_lines.side_effect = [order, received_order]
        repo.update.return_value = order

        await svc.receive_order(order.id)

        # No stock operations for a free-text-only order
        movement_repo.create.assert_not_called()
        item_repo.update_stock_and_pmp.assert_not_called()

    async def test_skips_line_when_inventory_item_not_found(self, po_mocks, mock_session):
        """If inventory item no longer exists, silently skip that line."""
        svc, repo, item_repo, movement_repo, supplier_item_repo = po_mocks
        item_id = uuid.uuid4()
        line = make_order_line(inventory_item_id=item_id)
        order = make_purchase_order(status="pending", lines=[line])
        received_order = make_purchase_order(status="received")

        repo.get_with_lines.side_effect = [order, received_order]
        item_repo.get_by_id.return_value = None  # item deleted
        repo.update.return_value = order

        await svc.receive_order(order.id)

        movement_repo.create.assert_not_called()

    async def test_updates_supplier_item_pricing_via_explicit_link(self, po_mocks, mock_session):
        svc, repo, item_repo, movement_repo, supplier_item_repo = po_mocks
        item_id = uuid.uuid4()
        supplier_item_id = uuid.uuid4()
        line = make_order_line(
            inventory_item_id=item_id,
            unit_cost=Decimal("5.00"),
            supplier_item_id=supplier_item_id,
        )
        order = make_purchase_order(status="pending", lines=[line])
        received_order = make_purchase_order(status="received")

        repo.get_with_lines.side_effect = [order, received_order]
        item_repo.get_by_id.return_value = make_inventory_item(id=item_id)
        movement_repo.create.return_value = MagicMock()
        movement_repo.calculate_pmp.return_value = Decimal("5.00")
        supplier_item = make_supplier_item(id=supplier_item_id)
        supplier_item_repo.get_by_id.return_value = supplier_item
        supplier_item_repo.get_by_supplier_and_item.return_value = None
        repo.update.return_value = order

        await svc.receive_order(order.id)

        supplier_item_repo.update.assert_called_once()
        update_dict = supplier_item_repo.update.call_args.args[1]
        assert update_dict["last_purchase_cost"] == Decimal("5.00")
        assert update_dict["unit_cost"] == Decimal("5.00")
        assert "last_purchase_date" in update_dict

    async def test_updates_supplier_item_pricing_via_fallback_lookup(self, po_mocks, mock_session):
        """When line.supplier_item_id is None, fall back to supplier+item lookup."""
        svc, repo, item_repo, movement_repo, supplier_item_repo = po_mocks
        item_id = uuid.uuid4()
        line = make_order_line(inventory_item_id=item_id, unit_cost=Decimal("4.20"))
        line.supplier_item_id = None
        order = make_purchase_order(status="pending", lines=[line])
        received_order = make_purchase_order(status="received")

        repo.get_with_lines.side_effect = [order, received_order]
        item_repo.get_by_id.return_value = make_inventory_item(id=item_id)
        movement_repo.create.return_value = MagicMock()
        movement_repo.calculate_pmp.return_value = Decimal("4.20")
        supplier_item = make_supplier_item()
        supplier_item_repo.get_by_supplier_and_item.return_value = supplier_item
        repo.update.return_value = order

        await svc.receive_order(order.id)

        supplier_item_repo.get_by_supplier_and_item.assert_called_once_with(
            order.supplier_id, item_id
        )
        supplier_item_repo.update.assert_called_once()

    async def test_no_supplier_item_update_when_not_found(self, po_mocks, mock_session):
        """If no SupplierItem link exists, pricing update is silently skipped."""
        svc, repo, item_repo, movement_repo, supplier_item_repo = po_mocks
        item_id = uuid.uuid4()
        line = make_order_line(inventory_item_id=item_id)
        line.supplier_item_id = None
        order = make_purchase_order(status="pending", lines=[line])
        received_order = make_purchase_order(status="received")

        repo.get_with_lines.side_effect = [order, received_order]
        item_repo.get_by_id.return_value = make_inventory_item(id=item_id)
        movement_repo.create.return_value = MagicMock()
        movement_repo.calculate_pmp.return_value = Decimal("2.00")
        supplier_item_repo.get_by_supplier_and_item.return_value = None
        repo.update.return_value = order

        await svc.receive_order(order.id)

        supplier_item_repo.update.assert_not_called()

    async def test_marks_order_as_received(self, po_mocks, mock_session):
        svc, repo, item_repo, movement_repo, supplier_item_repo = po_mocks
        order = make_purchase_order(status="pending", lines=[])
        received_order = make_purchase_order(status="received")

        repo.get_with_lines.side_effect = [order, received_order]
        repo.update.return_value = order

        await svc.receive_order(order.id)

        update_call = repo.update.call_args
        update_dict = update_call.args[1]
        assert update_dict["status"] == "received"
        assert "received_date" in update_dict

    async def test_commits_after_receive(self, po_mocks, mock_session):
        svc, repo, item_repo, movement_repo, supplier_item_repo = po_mocks
        order = make_purchase_order(status="pending", lines=[])
        received_order = make_purchase_order(status="received")

        repo.get_with_lines.side_effect = [order, received_order]
        repo.update.return_value = order

        await svc.receive_order(order.id)

        mock_session.commit.assert_called_once()


# ── cancel_order ───────────────────────────────────────────────────────────────


class TestCancelOrder:
    async def test_cancels_pending_order(self, po_mocks):
        svc, repo, *_ = po_mocks
        order = make_purchase_order(status="pending")
        cancelled_order = make_purchase_order(status="cancelled")
        repo.get_by_id.return_value = order
        repo.update.return_value = order
        repo.get_with_lines.return_value = cancelled_order

        result = await svc.cancel_order(order.id)

        repo.update.assert_called_once_with(order, {"status": "cancelled"})

    async def test_raises_404_when_not_found(self, po_mocks):
        svc, repo, *_ = po_mocks
        repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await svc.cancel_order(uuid.uuid4())

        assert exc_info.value.status_code == 404

    async def test_raises_409_when_already_received(self, po_mocks):
        svc, repo, *_ = po_mocks
        repo.get_by_id.return_value = make_purchase_order(status="received")

        with pytest.raises(HTTPException) as exc_info:
            await svc.cancel_order(uuid.uuid4())

        assert exc_info.value.status_code == 409
        assert "pending" in exc_info.value.detail

    async def test_raises_409_when_already_cancelled(self, po_mocks):
        svc, repo, *_ = po_mocks
        repo.get_by_id.return_value = make_purchase_order(status="cancelled")

        with pytest.raises(HTTPException) as exc_info:
            await svc.cancel_order(uuid.uuid4())

        assert exc_info.value.status_code == 409

    async def test_commits_after_cancel(self, po_mocks, mock_session):
        svc, repo, *_ = po_mocks
        order = make_purchase_order(status="pending")
        cancelled_order = make_purchase_order(status="cancelled")
        repo.get_by_id.return_value = order
        repo.update.return_value = order
        repo.get_with_lines.return_value = cancelled_order

        await svc.cancel_order(order.id)

        mock_session.commit.assert_called_once()

    async def test_returns_cancelled_order_response(self, po_mocks):
        svc, repo, *_ = po_mocks
        order = make_purchase_order(status="pending")
        cancelled_order = make_purchase_order(status="cancelled")
        repo.get_by_id.return_value = order
        repo.update.return_value = order
        repo.get_with_lines.return_value = cancelled_order

        result = await svc.cancel_order(order.id)

        assert result.status == "cancelled"
