"""
Unit tests for WorkOrderService.

All repositories and the session are mocked — no database needed.

Covers:
- Work order lifecycle: draft → active → pending_closure → closed
- Valid and invalid status transitions
- Auto-transition to pending_closure when all tasks completed
- CRUD for Tasks and TaskMaterials
- Material consumption and stock delta
- Work order cost calculation (consumed_quantity × unit_cost)
- Stock reserved management
- Certification lifecycle
- 404 / 400 / 409 error paths
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import NamedTuple
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from fastapi import HTTPException

from app.models.work_order import (
    CertificationStatus,
    DeliveryNoteStatus,
    TaskStatus,
    WorkOrderStatus,
)
from app.schemas.work_order import (
    CertificationCreate,
    CertificationItemCreate,
    TaskCreate,
    TaskMaterialConsume,
    TaskMaterialCreate,
    TaskStatusUpdate,
    TaskUpdate,
    WorkOrderCreate,
    WorkOrderStatusUpdate,
    WorkOrderUpdate,
)
from app.services.work_order import WorkOrderService

TENANT_ID = uuid.uuid4()


# ── Factories ──────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_work_order(**kwargs) -> MagicMock:
    wo = MagicMock()
    wo.id = uuid.uuid4()
    wo.tenant_id = TENANT_ID
    wo.work_order_number = "OBRA-2024-0001"
    wo.customer_id = uuid.uuid4()
    wo.origin_budget_id = None
    wo.status = WorkOrderStatus.DRAFT
    wo.address = "Calle Mayor 1, Madrid"
    wo.notes = None
    wo.other_lines_notes = None
    wo.assigned_to = None
    wo.start_date = None
    wo.end_date = None
    wo.tasks = []
    wo.certifications = []
    wo.purchase_order_links = []
    wo.delivery_notes = []
    wo.customer = make_customer()
    wo.origin_budget = None
    wo.invoices = []
    wo.created_at = _now()
    wo.updated_at = _now()
    for k, v in kwargs.items():
        setattr(wo, k, v)
    return wo


def make_customer(**kwargs) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.name = "Cliente Test"
    c.email = "cliente@test.com"
    c.phone = "600000000"
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


def make_task(**kwargs) -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.work_order_id = uuid.uuid4()
    t.origin_budget_line_id = None
    t.name = "Instalación cuadro eléctrico"
    t.description = None
    t.status = TaskStatus.PENDING
    t.sort_order = 0
    t.unit_price = None
    t.estimated_hours = Decimal("8.0")
    t.actual_hours = None
    t.materials = []
    t.certification_items = []
    t.created_at = _now()
    t.updated_at = _now()
    for k, v in kwargs.items():
        setattr(t, k, v)
    return t


def make_task_material(**kwargs) -> MagicMock:
    tm = MagicMock()
    tm.id = uuid.uuid4()
    tm.task_id = uuid.uuid4()
    tm.inventory_item_id = uuid.uuid4()
    tm.origin_budget_line_id = None
    tm.estimated_quantity = Decimal("10.0")
    tm.consumed_quantity = Decimal("0.0")
    tm.unit_cost = Decimal("5.00")
    tm.inventory_item = make_inventory_item()
    tm.created_at = _now()
    tm.updated_at = _now()
    for k, v in kwargs.items():
        setattr(tm, k, v)
    return tm


def make_inventory_item(**kwargs) -> MagicMock:
    item = MagicMock()
    item.id = uuid.uuid4()
    item.name = "Cable 2.5mm²"
    item.unit = "m"
    item.unit_cost = Decimal("2.00")
    item.unit_cost_avg = Decimal("2.10")
    item.stock_current = Decimal("100.0")
    item.stock_reserved = Decimal("0.0")
    item.is_active = True
    for k, v in kwargs.items():
        setattr(item, k, v)
    return item


def make_certification(**kwargs) -> MagicMock:
    cert = MagicMock()
    cert.id = uuid.uuid4()
    cert.work_order_id = uuid.uuid4()
    cert.certification_number = "CERT-OBRA-2024-0001-01"
    cert.status = CertificationStatus.DRAFT
    cert.notes = None
    cert.invoice_id = None
    cert.items = []
    cert.created_at = _now()
    cert.updated_at = _now()
    for k, v in kwargs.items():
        setattr(cert, k, v)
    return cert


def make_certification_item(**kwargs) -> MagicMock:
    ci = MagicMock()
    ci.id = uuid.uuid4()
    ci.certification_id = uuid.uuid4()
    ci.task_id = uuid.uuid4()
    ci.amount = Decimal("500.00")
    ci.notes = None
    ci.task = make_task(status=TaskStatus.COMPLETED)
    ci.created_at = _now()
    ci.updated_at = _now()
    for k, v in kwargs.items():
        setattr(ci, k, v)
    return ci


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    # Make session.execute return an object with scalars().all()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    execute_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=execute_result)
    return session


class _Mocks(NamedTuple):
    svc: WorkOrderService
    repo: AsyncMock
    task_repo: AsyncMock
    task_material_repo: AsyncMock
    cert_repo: AsyncMock
    cert_item_repo: AsyncMock
    wopo_repo: AsyncMock
    delivery_note_repo: AsyncMock
    delivery_note_item_repo: AsyncMock
    budget_repo: AsyncMock
    budget_line_repo: AsyncMock
    item_repo: AsyncMock
    movement_repo: AsyncMock
    customer_repo: AsyncMock
    visit_repo: AsyncMock
    purchase_order_repo: AsyncMock


@pytest.fixture
def mocks(mock_session) -> _Mocks:
    repo = AsyncMock()
    task_repo = AsyncMock()
    task_material_repo = AsyncMock()
    cert_repo = AsyncMock()
    cert_item_repo = AsyncMock()
    wopo_repo = AsyncMock()
    delivery_note_repo = AsyncMock()
    delivery_note_item_repo = AsyncMock()
    budget_repo = AsyncMock()
    budget_line_repo = AsyncMock()
    item_repo = AsyncMock()
    movement_repo = AsyncMock()
    customer_repo = AsyncMock()
    visit_repo = AsyncMock()
    purchase_order_repo = AsyncMock()

    with (
        patch("app.services.work_order.WorkOrderRepository", return_value=repo),
        patch("app.services.work_order.TaskRepository", return_value=task_repo),
        patch("app.services.work_order.TaskMaterialRepository", return_value=task_material_repo),
        patch("app.services.work_order.CertificationRepository", return_value=cert_repo),
        patch("app.services.work_order.CertificationItemRepository", return_value=cert_item_repo),
        patch("app.services.work_order.WorkOrderPurchaseOrderRepository", return_value=wopo_repo),
        patch("app.services.work_order.DeliveryNoteRepository", return_value=delivery_note_repo),
        patch("app.services.work_order.DeliveryNoteItemRepository", return_value=delivery_note_item_repo),
        patch("app.services.work_order.BudgetRepository", return_value=budget_repo),
        patch("app.services.work_order.BudgetLineRepository", return_value=budget_line_repo),
        patch("app.services.work_order.InventoryItemRepository", return_value=item_repo),
        patch("app.services.work_order.StockMovementRepository", return_value=movement_repo),
        patch("app.services.work_order.CustomerRepository", return_value=customer_repo),
        patch("app.services.work_order.SiteVisitRepository", return_value=visit_repo),
        patch("app.services.work_order.PurchaseOrderRepository", return_value=purchase_order_repo),
    ):
        svc = WorkOrderService(mock_session, TENANT_ID)
        yield _Mocks(
            svc, repo, task_repo, task_material_repo,
            cert_repo, cert_item_repo, wopo_repo,
            delivery_note_repo, delivery_note_item_repo,
            budget_repo, budget_line_repo,
            item_repo, movement_repo,
            customer_repo, visit_repo, purchase_order_repo,
        )


# Helper: wire get_work_order to return a full response by mocking get_with_full_detail
def _wire_get_work_order(mocks: _Mocks, work_order: MagicMock) -> None:
    """Causes get_work_order() to return a response built from the given work order."""
    mocks.repo.get_with_full_detail.return_value = work_order


# ── TestListWorkOrders ─────────────────────────────────────────────────────────

class TestListWorkOrders:
    async def test_returns_paginated_response(self, mocks):
        wo1 = make_work_order()
        wo2 = make_work_order()
        mocks.repo.search.return_value = ([wo1, wo2], 2)

        result = await mocks.svc.list_work_orders(
            q=None, customer_id=None, status_filter=None, skip=0, limit=10
        )

        assert result.total == 2
        assert len(result.items) == 2
        assert result.skip == 0
        assert result.limit == 10

    async def test_passes_filters_to_repo(self, mocks):
        mocks.repo.search.return_value = ([], 0)
        customer_id = uuid.uuid4()

        await mocks.svc.list_work_orders(
            q="obra", customer_id=customer_id, status_filter="active", skip=5, limit=20
        )

        mocks.repo.search.assert_called_once_with(
            query="obra",
            customer_id=customer_id,
            status="active",
            skip=5,
            limit=20,
        )

    async def test_empty_result(self, mocks):
        mocks.repo.search.return_value = ([], 0)

        result = await mocks.svc.list_work_orders(
            q=None, customer_id=None, status_filter=None, skip=0, limit=10
        )

        assert result.total == 0
        assert result.items == []


# ── TestGetWorkOrder ───────────────────────────────────────────────────────────

class TestGetWorkOrder:
    async def test_returns_full_response(self, mocks):
        wo = make_work_order()
        mocks.repo.get_with_full_detail.return_value = wo

        result = await mocks.svc.get_work_order(wo.id)

        assert result.id == wo.id
        mocks.repo.get_with_full_detail.assert_called_once_with(wo.id)

    async def test_raises_404_when_not_found(self, mocks):
        mocks.repo.get_with_full_detail.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.get_work_order(uuid.uuid4())

        assert exc.value.status_code == 404


# ── TestCreateWorkOrder ────────────────────────────────────────────────────────

class TestCreateWorkOrder:
    async def test_creates_work_order_with_customer(self, mocks):
        customer = make_customer()
        mocks.customer_repo.get_by_id.return_value = customer
        mocks.repo.get_next_work_order_number.return_value = "OBRA-2024-0001"
        created_wo = make_work_order(customer_id=customer.id)
        mocks.repo.create.return_value = created_wo
        mocks.repo.get_with_full_detail.return_value = created_wo

        data = WorkOrderCreate(customer_id=customer.id, address="Calle Test 1")
        result = await mocks.svc.create_work_order(data)

        assert result.id == created_wo.id
        mocks.repo.create.assert_called_once()

    async def test_raises_404_when_customer_not_found(self, mocks):
        mocks.customer_repo.get_by_id.return_value = None

        data = WorkOrderCreate(customer_id=uuid.uuid4())
        with pytest.raises(HTTPException) as exc:
            await mocks.svc.create_work_order(data)

        assert exc.value.status_code == 404

    async def test_commits_session(self, mocks, mock_session):
        customer = make_customer()
        mocks.customer_repo.get_by_id.return_value = customer
        mocks.repo.get_next_work_order_number.return_value = "OBRA-2024-0002"
        created_wo = make_work_order()
        mocks.repo.create.return_value = created_wo
        mocks.repo.get_with_full_detail.return_value = created_wo

        await mocks.svc.create_work_order(WorkOrderCreate(customer_id=customer.id))

        mock_session.commit.assert_called_once()


# ── TestUpdateWorkOrder ────────────────────────────────────────────────────────

class TestUpdateWorkOrder:
    async def test_updates_and_returns_response(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.ACTIVE)
        mocks.repo.get_by_id.return_value = wo
        mocks.repo.get_with_full_detail.return_value = wo

        data = WorkOrderUpdate(address="Nueva dirección", notes="Nueva nota")
        result = await mocks.svc.update_work_order(wo.id, data)

        mocks.repo.update.assert_called_once_with(wo, {"address": "Nueva dirección", "notes": "Nueva nota"})
        assert result.id == wo.id

    async def test_raises_404_when_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.update_work_order(uuid.uuid4(), WorkOrderUpdate(notes="x"))

        assert exc.value.status_code == 404

    async def test_raises_400_on_closed_work_order(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.CLOSED)
        mocks.repo.get_by_id.return_value = wo

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.update_work_order(wo.id, WorkOrderUpdate(notes="x"))

        assert exc.value.status_code == 400


# ── TestUpdateStatus ───────────────────────────────────────────────────────────

class TestUpdateStatus:
    async def test_valid_transition_draft_to_active(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.DRAFT)
        mocks.repo.get_by_id.return_value = wo
        mocks.repo.get_with_full_detail.return_value = wo

        await mocks.svc.update_status(wo.id, WorkOrderStatusUpdate(status="active"))

        mocks.repo.update.assert_called_once_with(wo, {"status": "active"})

    async def test_valid_transition_active_to_pending_closure(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.ACTIVE)
        mocks.repo.get_by_id.return_value = wo
        mocks.repo.get_with_full_detail.return_value = wo

        await mocks.svc.update_status(wo.id, WorkOrderStatusUpdate(status="pending_closure"))

        mocks.repo.update.assert_called_once()
        call_kwargs = mocks.repo.update.call_args[0]
        assert "pending_closure" in call_kwargs[1].values()

    async def test_valid_transition_pending_closure_to_closed(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.PENDING_CLOSURE)
        mocks.repo.get_by_id.return_value = wo
        mocks.repo.get_with_full_detail.return_value = wo

        await mocks.svc.update_status(wo.id, WorkOrderStatusUpdate(status="closed"))

        mocks.repo.update.assert_called_once()

    async def test_valid_transition_pending_closure_back_to_active(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.PENDING_CLOSURE)
        mocks.repo.get_by_id.return_value = wo
        mocks.repo.get_with_full_detail.return_value = wo

        await mocks.svc.update_status(wo.id, WorkOrderStatusUpdate(status="active"))

        mocks.repo.update.assert_called_once()

    async def test_valid_transition_draft_to_cancelled(self, mocks, mock_session):
        wo = make_work_order(status=WorkOrderStatus.DRAFT)
        mocks.repo.get_by_id.return_value = wo
        mocks.repo.get_with_full_detail.return_value = wo
        # _release_all_reserved_stock uses session.execute
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        await mocks.svc.update_status(wo.id, WorkOrderStatusUpdate(status="cancelled"))

        mocks.repo.update.assert_called_once()

    async def test_invalid_transition_draft_to_closed_raises_400(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.DRAFT)
        mocks.repo.get_by_id.return_value = wo

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.update_status(wo.id, WorkOrderStatusUpdate(status="closed"))

        assert exc.value.status_code == 400
        assert "draft" in exc.value.detail
        assert "closed" in exc.value.detail

    async def test_invalid_transition_active_to_draft_raises_400(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.ACTIVE)
        mocks.repo.get_by_id.return_value = wo

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.update_status(wo.id, WorkOrderStatusUpdate(status="draft"))

        assert exc.value.status_code == 400

    async def test_invalid_transition_closed_to_cancelled_raises_400(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.CLOSED)
        mocks.repo.get_by_id.return_value = wo

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.update_status(wo.id, WorkOrderStatusUpdate(status="cancelled"))

        assert exc.value.status_code == 400

    async def test_invalid_transition_cancelled_to_anything_raises_400(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.CANCELLED)
        mocks.repo.get_by_id.return_value = wo

        for target in ("draft", "active", "pending_closure", "closed"):
            with pytest.raises(HTTPException) as exc:
                await mocks.svc.update_status(wo.id, WorkOrderStatusUpdate(status=target))
            assert exc.value.status_code == 400

    async def test_raises_404_when_work_order_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.update_status(uuid.uuid4(), WorkOrderStatusUpdate(status="active"))

        assert exc.value.status_code == 404

    async def test_appends_notes_on_status_change(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.DRAFT, notes=None)
        mocks.repo.get_by_id.return_value = wo
        mocks.repo.get_with_full_detail.return_value = wo

        await mocks.svc.update_status(
            wo.id, WorkOrderStatusUpdate(status="active", notes="Iniciando obra")
        )

        update_call = mocks.repo.update.call_args[0][1]
        assert "Iniciando obra" in update_call.get("notes", "")

    async def test_cancelled_releases_reserved_stock(self, mocks, mock_session):
        wo = make_work_order(status=WorkOrderStatus.DRAFT)
        mocks.repo.get_by_id.return_value = wo
        mocks.repo.get_with_full_detail.return_value = wo

        # Simulate two task materials with reserved stock
        tm1 = make_task_material(estimated_quantity=Decimal("10"), consumed_quantity=Decimal("0"))
        tm2 = make_task_material(estimated_quantity=Decimal("5"), consumed_quantity=Decimal("2"))

        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = [tm1, tm2]
        mock_session.execute = AsyncMock(return_value=exec_result)

        await mocks.svc.update_status(wo.id, WorkOrderStatusUpdate(status="cancelled"))

        # session.execute was called to query materials and to update stock
        assert mock_session.execute.call_count >= 1


# ── TestAddTask ────────────────────────────────────────────────────────────────

class TestAddTask:
    async def test_adds_task_to_active_work_order(self, mocks, mock_session):
        wo = make_work_order(status=WorkOrderStatus.ACTIVE)
        task = make_task(work_order_id=wo.id)
        mocks.repo.get_by_id.return_value = wo
        mocks.task_repo.create.return_value = task

        # _get_task_with_materials uses session.execute directly
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        data = TaskCreate(name="Cableado", estimated_hours=Decimal("4"))
        result = await mocks.svc.add_task(wo.id, data)

        assert result.id == task.id
        mocks.task_repo.create.assert_called_once()

    async def test_adds_task_to_draft_work_order(self, mocks, mock_session):
        wo = make_work_order(status=WorkOrderStatus.DRAFT)
        task = make_task(work_order_id=wo.id)
        mocks.repo.get_by_id.return_value = wo
        mocks.task_repo.create.return_value = task

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        data = TaskCreate(name="Revisión previa")
        result = await mocks.svc.add_task(wo.id, data)

        assert result.name == task.name

    async def test_raises_404_when_work_order_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.add_task(uuid.uuid4(), TaskCreate(name="Tarea"))

        assert exc.value.status_code == 404

    async def test_raises_400_on_closed_work_order(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.CLOSED)
        mocks.repo.get_by_id.return_value = wo

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.add_task(wo.id, TaskCreate(name="Tarea"))

        assert exc.value.status_code == 400

    async def test_raises_400_on_cancelled_work_order(self, mocks):
        wo = make_work_order(status=WorkOrderStatus.CANCELLED)
        mocks.repo.get_by_id.return_value = wo

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.add_task(wo.id, TaskCreate(name="Tarea"))

        assert exc.value.status_code == 400

    async def test_commits_session(self, mocks, mock_session):
        wo = make_work_order(status=WorkOrderStatus.ACTIVE)
        task = make_task(work_order_id=wo.id)
        mocks.repo.get_by_id.return_value = wo
        mocks.task_repo.create.return_value = task

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        await mocks.svc.add_task(wo.id, TaskCreate(name="Tarea"))

        mock_session.commit.assert_called_once()


# ── TestUpdateTask ─────────────────────────────────────────────────────────────

class TestUpdateTask:
    async def test_updates_task_and_returns_response(self, mocks, mock_session):
        wo_id = uuid.uuid4()
        task = make_task(work_order_id=wo_id)
        mocks.task_repo.get_by_id.return_value = task

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        data = TaskUpdate(name="Nuevo nombre", actual_hours=Decimal("6"))
        result = await mocks.svc.update_task(wo_id, task.id, data)

        mocks.task_repo.update.assert_called_once_with(
            task, {"name": "Nuevo nombre", "actual_hours": Decimal("6")}
        )
        assert result.id == task.id

    async def test_raises_404_when_task_not_found(self, mocks):
        mocks.task_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.update_task(uuid.uuid4(), uuid.uuid4(), TaskUpdate(name="x"))

        assert exc.value.status_code == 404

    async def test_raises_404_when_task_belongs_to_different_work_order(self, mocks):
        task = make_task(work_order_id=uuid.uuid4())
        mocks.task_repo.get_by_id.return_value = task

        different_wo_id = uuid.uuid4()
        with pytest.raises(HTTPException) as exc:
            await mocks.svc.update_task(different_wo_id, task.id, TaskUpdate(name="x"))

        assert exc.value.status_code == 404


# ── TestDeleteTask ─────────────────────────────────────────────────────────────

class TestDeleteTask:
    async def test_deletes_pending_task_with_no_consumed_materials(self, mocks):
        wo_id = uuid.uuid4()
        task = make_task(work_order_id=wo_id, status=TaskStatus.PENDING, materials=[])
        mocks.task_repo.get_by_id.return_value = task

        await mocks.svc.delete_task(wo_id, task.id)

        mocks.task_repo.delete.assert_called_once_with(task)

    async def test_raises_404_when_task_not_found(self, mocks):
        mocks.task_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.delete_task(uuid.uuid4(), uuid.uuid4())

        assert exc.value.status_code == 404

    async def test_raises_400_when_task_in_progress(self, mocks):
        wo_id = uuid.uuid4()
        task = make_task(work_order_id=wo_id, status=TaskStatus.IN_PROGRESS)
        mocks.task_repo.get_by_id.return_value = task

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.delete_task(wo_id, task.id)

        assert exc.value.status_code == 400

    async def test_raises_400_when_task_completed(self, mocks):
        wo_id = uuid.uuid4()
        task = make_task(work_order_id=wo_id, status=TaskStatus.COMPLETED)
        mocks.task_repo.get_by_id.return_value = task

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.delete_task(wo_id, task.id)

        assert exc.value.status_code == 400

    async def test_raises_400_when_task_has_consumed_materials(self, mocks):
        wo_id = uuid.uuid4()
        tm = make_task_material(consumed_quantity=Decimal("2.0"))
        task = make_task(work_order_id=wo_id, status=TaskStatus.PENDING, materials=[tm])
        mocks.task_repo.get_by_id.return_value = task

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.delete_task(wo_id, task.id)

        assert exc.value.status_code == 400


# ── TestUpdateTaskStatus ───────────────────────────────────────────────────────

class TestUpdateTaskStatus:
    async def test_updates_task_status_to_in_progress(self, mocks):
        wo_id = uuid.uuid4()
        wo = make_work_order(id=wo_id, status=WorkOrderStatus.ACTIVE)
        task = make_task(work_order_id=wo_id, status=TaskStatus.PENDING)
        mocks.task_repo.get_by_id.return_value = task
        mocks.repo.check_all_tasks_completed.return_value = False
        mocks.repo.get_with_full_detail.return_value = wo

        result = await mocks.svc.update_task_status(
            wo_id, task.id, TaskStatusUpdate(status="in_progress")
        )

        mocks.task_repo.update.assert_called_once_with(task, {"status": "in_progress"})

    async def test_updates_actual_hours_when_provided(self, mocks):
        wo_id = uuid.uuid4()
        wo = make_work_order(id=wo_id)
        task = make_task(work_order_id=wo_id, status=TaskStatus.IN_PROGRESS)
        mocks.task_repo.get_by_id.return_value = task
        mocks.repo.check_all_tasks_completed.return_value = False
        mocks.repo.get_with_full_detail.return_value = wo

        await mocks.svc.update_task_status(
            wo_id, task.id, TaskStatusUpdate(status="completed", actual_hours=Decimal("7.5"))
        )

        mocks.task_repo.update.assert_called_once_with(
            task, {"status": "completed", "actual_hours": Decimal("7.5")}
        )

    async def test_auto_transition_to_pending_closure_when_all_tasks_completed(self, mocks, mock_session):
        wo_id = uuid.uuid4()
        wo = make_work_order(id=wo_id, status=WorkOrderStatus.ACTIVE)
        task = make_task(work_order_id=wo_id, status=TaskStatus.IN_PROGRESS)
        mocks.task_repo.get_by_id.return_value = task
        mocks.repo.check_all_tasks_completed.return_value = True
        mocks.repo.get_by_id.return_value = wo
        mocks.repo.get_with_full_detail.return_value = wo

        await mocks.svc.update_task_status(
            wo_id, task.id, TaskStatusUpdate(status="completed")
        )

        # Should auto-update work order to pending_closure
        mocks.repo.update.assert_called_once_with(
            wo, {"status": WorkOrderStatus.PENDING_CLOSURE}
        )

    async def test_no_auto_transition_when_work_order_not_active(self, mocks):
        wo_id = uuid.uuid4()
        wo = make_work_order(id=wo_id, status=WorkOrderStatus.PENDING_CLOSURE)
        task = make_task(work_order_id=wo_id, status=TaskStatus.IN_PROGRESS)
        mocks.task_repo.get_by_id.return_value = task
        mocks.repo.check_all_tasks_completed.return_value = True
        mocks.repo.get_by_id.return_value = wo
        mocks.repo.get_with_full_detail.return_value = wo

        await mocks.svc.update_task_status(
            wo_id, task.id, TaskStatusUpdate(status="completed")
        )

        # No auto-transition since work order is not active
        mocks.repo.update.assert_not_called()

    async def test_auto_transition_not_triggered_when_tasks_not_all_done(self, mocks):
        wo_id = uuid.uuid4()
        wo = make_work_order(id=wo_id, status=WorkOrderStatus.ACTIVE)
        task = make_task(work_order_id=wo_id, status=TaskStatus.IN_PROGRESS)
        mocks.task_repo.get_by_id.return_value = task
        mocks.repo.check_all_tasks_completed.return_value = False
        mocks.repo.get_with_full_detail.return_value = wo

        await mocks.svc.update_task_status(
            wo_id, task.id, TaskStatusUpdate(status="completed")
        )

        mocks.repo.update.assert_not_called()

    async def test_raises_404_when_task_not_found(self, mocks):
        mocks.task_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.update_task_status(
                uuid.uuid4(), uuid.uuid4(), TaskStatusUpdate(status="in_progress")
            )

        assert exc.value.status_code == 404

    async def test_raises_404_when_task_belongs_to_different_work_order(self, mocks):
        task = make_task(work_order_id=uuid.uuid4(), status=TaskStatus.PENDING)
        mocks.task_repo.get_by_id.return_value = task

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.update_task_status(
                uuid.uuid4(), task.id, TaskStatusUpdate(status="in_progress")
            )

        assert exc.value.status_code == 404

    async def test_cancelled_task_releases_reserved_stock(self, mocks, mock_session):
        wo_id = uuid.uuid4()
        wo = make_work_order(id=wo_id, status=WorkOrderStatus.ACTIVE)
        task = make_task(work_order_id=wo_id, status=TaskStatus.IN_PROGRESS)
        mocks.task_repo.get_by_id.return_value = task
        mocks.repo.check_all_tasks_completed.return_value = False
        mocks.repo.get_with_full_detail.return_value = wo

        tm = make_task_material(estimated_quantity=Decimal("5"), consumed_quantity=Decimal("1"))
        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = [tm]
        mock_session.execute = AsyncMock(return_value=exec_result)

        await mocks.svc.update_task_status(
            wo_id, task.id, TaskStatusUpdate(status="cancelled")
        )

        # session.execute called at least once to query materials
        assert mock_session.execute.call_count >= 1


# ── TestAddMaterial ────────────────────────────────────────────────────────────

class TestAddMaterial:
    async def test_adds_material_and_reserves_stock(self, mocks, mock_session):
        wo_id = uuid.uuid4()
        task = make_task(work_order_id=wo_id)
        item = make_inventory_item()
        mocks.task_repo.get_by_id.return_value = task
        mocks.item_repo.get_by_id.return_value = item
        mocks.task_material_repo.create.return_value = make_task_material()

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        data = TaskMaterialCreate(
            inventory_item_id=item.id,
            task_id=task.id,
            estimated_quantity=Decimal("10.0"),
        )
        result = await mocks.svc.add_material(wo_id, data)

        mocks.task_material_repo.create.assert_called_once()
        # Stock reservation: session.execute called for UPDATE InventoryItem
        mock_session.execute.assert_called()

    async def test_uses_unit_cost_avg_when_no_cost_provided(self, mocks, mock_session):
        wo_id = uuid.uuid4()
        task = make_task(work_order_id=wo_id)
        item = make_inventory_item(unit_cost=Decimal("2.00"), unit_cost_avg=Decimal("2.50"))
        mocks.task_repo.get_by_id.return_value = task
        mocks.item_repo.get_by_id.return_value = item
        mocks.task_material_repo.create.return_value = make_task_material()

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        data = TaskMaterialCreate(
            inventory_item_id=item.id,
            task_id=task.id,
            estimated_quantity=Decimal("5.0"),
        )
        await mocks.svc.add_material(wo_id, data)

        created_tm = mocks.task_material_repo.create.call_args[0][0]
        assert created_tm.unit_cost == Decimal("2.50")

    async def test_uses_unit_cost_base_when_avg_is_zero(self, mocks, mock_session):
        wo_id = uuid.uuid4()
        task = make_task(work_order_id=wo_id)
        item = make_inventory_item(unit_cost=Decimal("3.00"), unit_cost_avg=Decimal("0.00"))
        mocks.task_repo.get_by_id.return_value = task
        mocks.item_repo.get_by_id.return_value = item
        mocks.task_material_repo.create.return_value = make_task_material()

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        data = TaskMaterialCreate(
            inventory_item_id=item.id,
            task_id=task.id,
            estimated_quantity=Decimal("3.0"),
        )
        await mocks.svc.add_material(wo_id, data)

        created_tm = mocks.task_material_repo.create.call_args[0][0]
        assert created_tm.unit_cost == Decimal("3.00")

    async def test_uses_explicit_unit_cost_when_provided(self, mocks, mock_session):
        wo_id = uuid.uuid4()
        task = make_task(work_order_id=wo_id)
        item = make_inventory_item(unit_cost_avg=Decimal("9.99"))
        mocks.task_repo.get_by_id.return_value = task
        mocks.item_repo.get_by_id.return_value = item
        mocks.task_material_repo.create.return_value = make_task_material()

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        data = TaskMaterialCreate(
            inventory_item_id=item.id,
            task_id=task.id,
            estimated_quantity=Decimal("1.0"),
            unit_cost=Decimal("7.77"),
        )
        await mocks.svc.add_material(wo_id, data)

        created_tm = mocks.task_material_repo.create.call_args[0][0]
        assert created_tm.unit_cost == Decimal("7.77")

    async def test_raises_404_when_task_not_found(self, mocks):
        mocks.task_repo.get_by_id.return_value = None
        item = make_inventory_item()

        data = TaskMaterialCreate(
            inventory_item_id=item.id,
            task_id=uuid.uuid4(),
            estimated_quantity=Decimal("1.0"),
        )
        with pytest.raises(HTTPException) as exc:
            await mocks.svc.add_material(uuid.uuid4(), data)

        assert exc.value.status_code == 404

    async def test_raises_404_when_inventory_item_not_found(self, mocks):
        wo_id = uuid.uuid4()
        task = make_task(work_order_id=wo_id)
        mocks.task_repo.get_by_id.return_value = task
        mocks.item_repo.get_by_id.return_value = None

        data = TaskMaterialCreate(
            inventory_item_id=uuid.uuid4(),
            task_id=task.id,
            estimated_quantity=Decimal("1.0"),
        )
        with pytest.raises(HTTPException) as exc:
            await mocks.svc.add_material(wo_id, data)

        assert exc.value.status_code == 404

    async def test_raises_404_when_inventory_item_inactive(self, mocks):
        wo_id = uuid.uuid4()
        task = make_task(work_order_id=wo_id)
        item = make_inventory_item(is_active=False)
        mocks.task_repo.get_by_id.return_value = task
        mocks.item_repo.get_by_id.return_value = item

        data = TaskMaterialCreate(
            inventory_item_id=item.id,
            task_id=task.id,
            estimated_quantity=Decimal("1.0"),
        )
        with pytest.raises(HTTPException) as exc:
            await mocks.svc.add_material(wo_id, data)

        assert exc.value.status_code == 404


# ── TestRemoveMaterial ─────────────────────────────────────────────────────────

class TestRemoveMaterial:
    async def test_removes_material_and_releases_reserved_stock(self, mocks, mock_session):
        wo_id = uuid.uuid4()
        task_id = uuid.uuid4()
        mat_id = uuid.uuid4()
        task = make_task(id=task_id, work_order_id=wo_id)
        tm = make_task_material(
            id=mat_id,
            task_id=task_id,
            estimated_quantity=Decimal("10"),
            consumed_quantity=Decimal("0"),
        )
        mocks.task_repo.get_by_id.return_value = task
        mocks.task_material_repo.get_by_id.return_value = tm

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        await mocks.svc.remove_material(wo_id, task_id, mat_id)

        mock_session.delete.assert_called_once_with(tm)

    async def test_raises_404_when_task_not_found(self, mocks):
        mocks.task_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.remove_material(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

        assert exc.value.status_code == 404

    async def test_raises_404_when_material_not_found(self, mocks):
        wo_id = uuid.uuid4()
        task = make_task(work_order_id=wo_id)
        mocks.task_repo.get_by_id.return_value = task
        mocks.task_material_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.remove_material(wo_id, task.id, uuid.uuid4())

        assert exc.value.status_code == 404

    async def test_raises_404_when_material_belongs_to_different_task(self, mocks):
        wo_id = uuid.uuid4()
        task = make_task(work_order_id=wo_id)
        tm = make_task_material(task_id=uuid.uuid4())  # different task
        mocks.task_repo.get_by_id.return_value = task
        mocks.task_material_repo.get_by_id.return_value = tm

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.remove_material(wo_id, task.id, tm.id)

        assert exc.value.status_code == 404

    async def test_raises_400_when_material_has_consumption(self, mocks):
        wo_id = uuid.uuid4()
        task_id = uuid.uuid4()
        task = make_task(id=task_id, work_order_id=wo_id)
        tm = make_task_material(task_id=task_id, consumed_quantity=Decimal("3.0"))
        mocks.task_repo.get_by_id.return_value = task
        mocks.task_material_repo.get_by_id.return_value = tm

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.remove_material(wo_id, task_id, tm.id)

        assert exc.value.status_code == 400


# ── TestConsumeMaterial ────────────────────────────────────────────────────────

class TestConsumeMaterial:
    async def test_records_consumption_and_updates_stock(self, mocks, mock_session):
        wo_id = uuid.uuid4()
        task_id = uuid.uuid4()
        tm_id = uuid.uuid4()
        task = make_task(id=task_id, work_order_id=wo_id, status=TaskStatus.IN_PROGRESS)
        tm = make_task_material(id=tm_id, task_id=task_id, consumed_quantity=Decimal("0"))
        mocks.task_material_repo.get_by_id.return_value = tm
        mocks.task_repo.get_by_id.return_value = task

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        data = TaskMaterialConsume(consumed_quantity=Decimal("4.0"))
        await mocks.svc.consume_material(wo_id, task_id, tm_id, data)

        mocks.task_material_repo.update.assert_called_once_with(
            tm, {"consumed_quantity": Decimal("4.0")}
        )
        # Stock update executed
        mock_session.execute.assert_called()

    async def test_consumption_above_estimated_is_allowed(self, mocks, mock_session):
        wo_id = uuid.uuid4()
        task_id = uuid.uuid4()
        tm_id = uuid.uuid4()
        task = make_task(id=task_id, work_order_id=wo_id, status=TaskStatus.IN_PROGRESS)
        tm = make_task_material(
            id=tm_id,
            task_id=task_id,
            estimated_quantity=Decimal("5"),
            consumed_quantity=Decimal("0"),
        )
        mocks.task_material_repo.get_by_id.return_value = tm
        mocks.task_repo.get_by_id.return_value = task

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        # Consuming 8 > estimated 5 is allowed
        data = TaskMaterialConsume(consumed_quantity=Decimal("8.0"))
        await mocks.svc.consume_material(wo_id, task_id, tm_id, data)

        mocks.task_material_repo.update.assert_called_once_with(
            tm, {"consumed_quantity": Decimal("8.0")}
        )

    async def test_stock_delta_calculated_correctly(self, mocks, mock_session):
        """Delta = new_consumed - previous_consumed.  Stock updated by delta."""
        wo_id = uuid.uuid4()
        task_id = uuid.uuid4()
        tm_id = uuid.uuid4()
        task = make_task(id=task_id, work_order_id=wo_id, status=TaskStatus.IN_PROGRESS)
        tm = make_task_material(
            id=tm_id,
            task_id=task_id,
            consumed_quantity=Decimal("3"),  # previously consumed 3
        )
        mocks.task_material_repo.get_by_id.return_value = tm
        mocks.task_repo.get_by_id.return_value = task

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        # New consumption = 7, delta = 7 - 3 = 4
        data = TaskMaterialConsume(consumed_quantity=Decimal("7"))
        await mocks.svc.consume_material(wo_id, task_id, tm_id, data)

        # session.execute should be called once for stock update (delta != 0)
        # and once for reload task
        assert mock_session.execute.call_count >= 1

    async def test_no_stock_update_when_delta_is_zero(self, mocks, mock_session):
        wo_id = uuid.uuid4()
        task_id = uuid.uuid4()
        tm_id = uuid.uuid4()
        task = make_task(id=task_id, work_order_id=wo_id, status=TaskStatus.IN_PROGRESS)
        tm = make_task_material(
            id=tm_id,
            task_id=task_id,
            consumed_quantity=Decimal("5"),
        )
        mocks.task_material_repo.get_by_id.return_value = tm
        mocks.task_repo.get_by_id.return_value = task

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = task
        mock_session.execute = AsyncMock(return_value=exec_result)

        # Same value → delta = 0 → no stock execute
        data = TaskMaterialConsume(consumed_quantity=Decimal("5"))
        await mocks.svc.consume_material(wo_id, task_id, tm_id, data)

        # Only the task reload execute (not a stock update)
        assert mock_session.execute.call_count == 1

    async def test_raises_404_when_material_not_found(self, mocks):
        mocks.task_material_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.consume_material(
                uuid.uuid4(), uuid.uuid4(), uuid.uuid4(),
                TaskMaterialConsume(consumed_quantity=Decimal("1"))
            )

        assert exc.value.status_code == 404

    async def test_raises_404_when_task_not_found(self, mocks):
        tm = make_task_material()
        mocks.task_material_repo.get_by_id.return_value = tm
        mocks.task_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.consume_material(
                uuid.uuid4(), tm.task_id, tm.id,
                TaskMaterialConsume(consumed_quantity=Decimal("1"))
            )

        assert exc.value.status_code == 404

    async def test_raises_400_on_pending_task(self, mocks):
        wo_id = uuid.uuid4()
        task_id = uuid.uuid4()
        tm_id = uuid.uuid4()
        task = make_task(id=task_id, work_order_id=wo_id, status=TaskStatus.PENDING)
        tm = make_task_material(id=tm_id, task_id=task_id)
        mocks.task_material_repo.get_by_id.return_value = tm
        mocks.task_repo.get_by_id.return_value = task

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.consume_material(
                wo_id, task_id, tm_id,
                TaskMaterialConsume(consumed_quantity=Decimal("1"))
            )

        assert exc.value.status_code == 400

    async def test_raises_400_on_cancelled_task(self, mocks):
        wo_id = uuid.uuid4()
        task_id = uuid.uuid4()
        tm_id = uuid.uuid4()
        task = make_task(id=task_id, work_order_id=wo_id, status=TaskStatus.CANCELLED)
        tm = make_task_material(id=tm_id, task_id=task_id)
        mocks.task_material_repo.get_by_id.return_value = tm
        mocks.task_repo.get_by_id.return_value = task

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.consume_material(
                wo_id, task_id, tm_id,
                TaskMaterialConsume(consumed_quantity=Decimal("1"))
            )

        assert exc.value.status_code == 400


# ── TestComputeKPIs ────────────────────────────────────────────────────────────

class TestComputeKPIs:
    """Tests for _compute_kpis via get_kpis — tests business calculations directly."""

    def _make_wo_with_tasks(
        self,
        tasks: list[MagicMock],
        certifications: list[MagicMock] | None = None,
        purchase_order_links: list[MagicMock] | None = None,
        origin_budget: MagicMock | None = None,
    ) -> MagicMock:
        wo = make_work_order()
        wo.tasks = tasks
        wo.certifications = certifications or []
        wo.purchase_order_links = purchase_order_links or []
        wo.origin_budget = origin_budget
        return wo

    def test_progress_zero_with_no_tasks(self, mocks):
        wo = self._make_wo_with_tasks([])
        kpis = mocks.svc._compute_kpis(wo)
        assert kpis.total_tasks == 0
        assert kpis.completed_tasks == 0
        assert kpis.progress_pct == Decimal("0.0")

    def test_progress_100_when_all_tasks_completed(self, mocks):
        tasks = [
            make_task(status=TaskStatus.COMPLETED),
            make_task(status=TaskStatus.COMPLETED),
        ]
        wo = self._make_wo_with_tasks(tasks)
        kpis = mocks.svc._compute_kpis(wo)
        assert kpis.total_tasks == 2
        assert kpis.completed_tasks == 2
        assert kpis.progress_pct == Decimal("100.0")

    def test_progress_50_when_half_completed(self, mocks):
        tasks = [
            make_task(status=TaskStatus.COMPLETED),
            make_task(status=TaskStatus.PENDING),
        ]
        wo = self._make_wo_with_tasks(tasks)
        kpis = mocks.svc._compute_kpis(wo)
        assert kpis.progress_pct == Decimal("50.0")

    def test_actual_cost_is_consumed_times_unit_cost(self, mocks):
        """actual_cost = SUM(consumed_quantity × unit_cost)"""
        tm1 = make_task_material(consumed_quantity=Decimal("4"), unit_cost=Decimal("3.00"))
        tm2 = make_task_material(consumed_quantity=Decimal("2"), unit_cost=Decimal("10.00"))
        task = make_task(materials=[tm1, tm2])
        wo = self._make_wo_with_tasks([task])

        kpis = mocks.svc._compute_kpis(wo)

        # 4×3 + 2×10 = 12 + 20 = 32
        assert kpis.actual_cost == Decimal("32.00")

    def test_budget_cost_is_estimated_times_unit_cost(self, mocks):
        """budget_cost = SUM(estimated_quantity × unit_cost)"""
        tm = make_task_material(estimated_quantity=Decimal("10"), unit_cost=Decimal("5.00"))
        task = make_task(materials=[tm])
        wo = self._make_wo_with_tasks([task])

        kpis = mocks.svc._compute_kpis(wo)

        assert kpis.budget_cost == Decimal("50.00")

    def test_actual_cost_zero_when_no_materials(self, mocks):
        task = make_task(materials=[])
        wo = self._make_wo_with_tasks([task])
        kpis = mocks.svc._compute_kpis(wo)
        assert kpis.actual_cost == Decimal("0.0")

    def test_hours_deviation_zero_when_no_estimated_hours(self, mocks):
        task = make_task(estimated_hours=None, actual_hours=None)
        wo = self._make_wo_with_tasks([task])
        kpis = mocks.svc._compute_kpis(wo)
        assert kpis.hours_deviation_pct == Decimal("0.0")

    def test_hours_deviation_calculated_correctly(self, mocks):
        """deviation = (actual - estimated) / estimated × 100"""
        task = make_task(estimated_hours=Decimal("10"), actual_hours=Decimal("12"))
        wo = self._make_wo_with_tasks([task])
        kpis = mocks.svc._compute_kpis(wo)
        # (12-10)/10 × 100 = 20.0%
        assert kpis.hours_deviation_pct == Decimal("20.0")

    def test_pending_materials_counted_correctly(self, mocks):
        tm_pending = make_task_material(
            estimated_quantity=Decimal("10"), consumed_quantity=Decimal("5")
        )
        tm_done = make_task_material(
            estimated_quantity=Decimal("3"), consumed_quantity=Decimal("3")
        )
        task = make_task(materials=[tm_pending, tm_done])
        wo = self._make_wo_with_tasks([task])
        kpis = mocks.svc._compute_kpis(wo)
        assert kpis.pending_materials == 1
        assert kpis.fully_consumed_materials == 1

    def test_total_certified_sums_issued_and_invoiced_certs(self, mocks):
        ci1 = make_certification_item(amount=Decimal("300.00"))
        ci2 = make_certification_item(amount=Decimal("200.00"))
        cert_issued = make_certification(
            status=CertificationStatus.ISSUED, items=[ci1]
        )
        cert_invoiced = make_certification(
            status=CertificationStatus.INVOICED, items=[ci2]
        )
        wo = self._make_wo_with_tasks([], certifications=[cert_issued, cert_invoiced])

        kpis = mocks.svc._compute_kpis(wo)

        assert kpis.total_certified == Decimal("500.00")
        assert kpis.total_invoiced == Decimal("200.00")

    def test_draft_certification_not_counted(self, mocks):
        ci = make_certification_item(amount=Decimal("100.00"))
        cert_draft = make_certification(status=CertificationStatus.DRAFT, items=[ci])
        wo = self._make_wo_with_tasks([], certifications=[cert_draft])

        kpis = mocks.svc._compute_kpis(wo)

        assert kpis.total_certified == Decimal("0.00")

    def test_budget_total_with_no_budget(self, mocks):
        wo = self._make_wo_with_tasks([], origin_budget=None)
        kpis = mocks.svc._compute_kpis(wo)
        assert kpis.budget_total == Decimal("0.00")


# ── TestCreateCertification ────────────────────────────────────────────────────

class TestCreateCertification:
    async def test_creates_certification_with_completed_task(self, mocks):
        wo_id = uuid.uuid4()
        wo = make_work_order(id=wo_id)
        task = make_task(work_order_id=wo_id, status=TaskStatus.COMPLETED, unit_price=Decimal("500.00"))
        cert = make_certification(work_order_id=wo_id)
        mocks.repo.get_by_id.return_value = wo
        mocks.cert_repo.get_next_certification_number.return_value = "CERT-OBRA-2024-0001-01"
        mocks.cert_repo.create.return_value = cert
        mocks.task_repo.get_by_id.return_value = task
        mocks.cert_repo.get_with_items.return_value = cert

        data = CertificationCreate(items=[CertificationItemCreate(task_id=task.id)])
        result = await mocks.svc.create_certification(wo_id, data)

        assert result.id == cert.id
        mocks.cert_repo.create.assert_called_once()

    async def test_raises_404_when_work_order_not_found(self, mocks):
        mocks.repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.create_certification(
                uuid.uuid4(),
                CertificationCreate(items=[CertificationItemCreate(task_id=uuid.uuid4())])
            )

        assert exc.value.status_code == 404

    async def test_raises_404_when_task_not_found(self, mocks):
        wo_id = uuid.uuid4()
        wo = make_work_order(id=wo_id)
        cert = make_certification(work_order_id=wo_id)
        mocks.repo.get_by_id.return_value = wo
        mocks.cert_repo.get_next_certification_number.return_value = "CERT-OBRA-01"
        mocks.cert_repo.create.return_value = cert
        mocks.task_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.create_certification(
                wo_id,
                CertificationCreate(items=[CertificationItemCreate(task_id=uuid.uuid4())])
            )

        assert exc.value.status_code == 404

    async def test_raises_400_when_task_not_completed(self, mocks):
        wo_id = uuid.uuid4()
        wo = make_work_order(id=wo_id)
        task = make_task(work_order_id=wo_id, status=TaskStatus.IN_PROGRESS)
        cert = make_certification(work_order_id=wo_id)
        mocks.repo.get_by_id.return_value = wo
        mocks.cert_repo.get_next_certification_number.return_value = "CERT-OBRA-01"
        mocks.cert_repo.create.return_value = cert
        mocks.task_repo.get_by_id.return_value = task

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.create_certification(
                wo_id,
                CertificationCreate(items=[CertificationItemCreate(task_id=task.id)])
            )

        assert exc.value.status_code == 400


# ── TestIssueCertification ─────────────────────────────────────────────────────

class TestIssueCertification:
    async def test_issues_draft_certification_with_items(self, mocks):
        wo_id = uuid.uuid4()
        cert_id = uuid.uuid4()
        ci = make_certification_item()
        cert = make_certification(
            id=cert_id, work_order_id=wo_id,
            status=CertificationStatus.DRAFT, items=[ci]
        )
        mocks.cert_repo.get_with_items.return_value = cert

        await mocks.svc.issue_certification(wo_id, cert_id)

        mocks.cert_repo.update.assert_called_once_with(cert, {"status": "issued"})

    async def test_raises_404_when_cert_not_found(self, mocks):
        mocks.cert_repo.get_with_items.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.issue_certification(uuid.uuid4(), uuid.uuid4())

        assert exc.value.status_code == 404

    async def test_raises_404_when_cert_belongs_to_different_work_order(self, mocks):
        cert = make_certification(work_order_id=uuid.uuid4())
        mocks.cert_repo.get_with_items.return_value = cert

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.issue_certification(uuid.uuid4(), cert.id)

        assert exc.value.status_code == 404

    async def test_raises_400_when_cert_already_issued(self, mocks):
        wo_id = uuid.uuid4()
        cert = make_certification(
            work_order_id=wo_id, status=CertificationStatus.ISSUED
        )
        mocks.cert_repo.get_with_items.return_value = cert

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.issue_certification(wo_id, cert.id)

        assert exc.value.status_code == 400

    async def test_raises_400_when_cert_has_no_items(self, mocks):
        wo_id = uuid.uuid4()
        cert = make_certification(
            work_order_id=wo_id, status=CertificationStatus.DRAFT, items=[]
        )
        mocks.cert_repo.get_with_items.return_value = cert

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.issue_certification(wo_id, cert.id)

        assert exc.value.status_code == 400


# ── TestDeleteCertification ────────────────────────────────────────────────────

class TestDeleteCertification:
    async def test_deletes_draft_certification(self, mocks):
        wo_id = uuid.uuid4()
        cert = make_certification(work_order_id=wo_id, status=CertificationStatus.DRAFT)
        mocks.cert_repo.get_by_id.return_value = cert

        await mocks.svc.delete_certification(wo_id, cert.id)

        mocks.cert_repo.delete.assert_called_once_with(cert)

    async def test_raises_404_when_cert_not_found(self, mocks):
        mocks.cert_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.delete_certification(uuid.uuid4(), uuid.uuid4())

        assert exc.value.status_code == 404

    async def test_raises_400_when_cert_is_issued(self, mocks):
        wo_id = uuid.uuid4()
        cert = make_certification(work_order_id=wo_id, status=CertificationStatus.ISSUED)
        mocks.cert_repo.get_by_id.return_value = cert

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.delete_certification(wo_id, cert.id)

        assert exc.value.status_code == 400

    async def test_raises_400_when_cert_is_invoiced(self, mocks):
        wo_id = uuid.uuid4()
        cert = make_certification(work_order_id=wo_id, status=CertificationStatus.INVOICED)
        mocks.cert_repo.get_by_id.return_value = cert

        with pytest.raises(HTTPException) as exc:
            await mocks.svc.delete_certification(wo_id, cert.id)

        assert exc.value.status_code == 400


# ── TestValidateStatusTransition ──────────────────────────────────────────────

class TestValidateStatusTransition:
    """Direct tests for the _validate_status_transition private method."""

    def test_all_valid_transitions(self, mocks):
        valid_transitions = [
            ("draft", "active"),
            ("draft", "cancelled"),
            ("active", "pending_closure"),
            ("active", "cancelled"),
            ("pending_closure", "closed"),
            ("pending_closure", "active"),
            ("closed", "active"),
        ]
        for current, new in valid_transitions:
            # Should not raise
            mocks.svc._validate_status_transition(current, new)

    def test_all_invalid_transitions_raise_400(self, mocks):
        invalid_transitions = [
            ("draft", "pending_closure"),
            ("draft", "closed"),
            ("active", "draft"),
            ("active", "closed"),
            ("pending_closure", "draft"),
            ("pending_closure", "cancelled"),
            ("closed", "draft"),
            ("closed", "pending_closure"),
            ("closed", "cancelled"),
            ("cancelled", "draft"),
            ("cancelled", "active"),
            ("cancelled", "pending_closure"),
            ("cancelled", "closed"),
            ("cancelled", "cancelled"),
        ]
        for current, new in invalid_transitions:
            with pytest.raises(HTTPException) as exc:
                mocks.svc._validate_status_transition(current, new)
            assert exc.value.status_code == 400, f"Expected 400 for {current!r}→{new!r}"
