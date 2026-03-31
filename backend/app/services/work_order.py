"""Service layer for the WorkOrder module."""

from __future__ import annotations

import logging
import re
import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_item import InventoryItem
from app.models.stock_movement import StockMovement
from app.models.work_order import (
    Certification,
    CertificationItem,
    DeliveryNote,
    DeliveryNoteItem,
    DeliveryNoteStatus,
    Task,
    TaskMaterial,
    TaskStatus,
    WorkOrder,
    WorkOrderPurchaseOrder,
    WorkOrderStatus,
)
from app.repositories.budget import BudgetLineRepository, BudgetRepository
from app.repositories.customer import CustomerRepository
from app.repositories.inventory_item import InventoryItemRepository
from app.repositories.purchase_order import PurchaseOrderRepository
from app.repositories.site_visit import SiteVisitRepository
from app.repositories.stock_movement import StockMovementRepository
from app.repositories.work_order import (
    CertificationItemRepository,
    CertificationRepository,
    DeliveryNoteItemRepository,
    DeliveryNoteRepository,
    TaskMaterialRepository,
    TaskRepository,
    WorkOrderPurchaseOrderRepository,
    WorkOrderRepository,
)
from app.schemas.work_order import (
    CertificationCreate,
    CertificationItemResponse,
    CertificationResponse,
    DeliveryNoteCreate,
    DeliveryNoteItemResponse,
    DeliveryNoteResponse,
    DeliveryNoteUpdate,
    LinkedPurchaseOrderResponse,
    SendDocumentEmail,
    TaskCreate,
    TaskMaterialConsume,
    TaskMaterialCreate,
    TaskMaterialResponse,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
    WhatsAppLinkResponse,
    WorkOrderCreate,
    WorkOrderKPIs,
    WorkOrderListResponse,
    WorkOrderPurchaseOrderLink,
    WorkOrderResponse,
    WorkOrderStatusUpdate,
    WorkOrderSummary,
    WorkOrderUpdate,
)

logger = logging.getLogger(__name__)


class WorkOrderService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = WorkOrderRepository(session)
        self._task_repo = TaskRepository(session)
        self._task_material_repo = TaskMaterialRepository(session)
        self._cert_repo = CertificationRepository(session)
        self._cert_item_repo = CertificationItemRepository(session)
        self._wopo_repo = WorkOrderPurchaseOrderRepository(session)
        self._delivery_note_repo = DeliveryNoteRepository(session)
        self._delivery_note_item_repo = DeliveryNoteItemRepository(session)
        self._budget_repo = BudgetRepository(session)
        self._budget_line_repo = BudgetLineRepository(session)
        self._item_repo = InventoryItemRepository(session)
        self._movement_repo = StockMovementRepository(session)
        self._customer_repo = CustomerRepository(session)
        self._visit_repo = SiteVisitRepository(session)
        self._purchase_order_repo = PurchaseOrderRepository(session)

    # ── Create directly ───────────────────────────────────────────────────────

    async def create_work_order(self, data: WorkOrderCreate) -> WorkOrderResponse:
        """Creates a standalone WorkOrder not linked to any budget."""
        customer = await self._customer_repo.get_by_id(data.customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado",
            )

        work_order_number = await self._repo.get_next_work_order_number()
        work_order = WorkOrder(
            work_order_number=work_order_number,
            customer_id=data.customer_id,
            origin_budget_id=None,
            status=WorkOrderStatus.DRAFT,
            address=data.address,
            notes=data.notes,
        )
        work_order = await self._repo.create(work_order)
        await self._session.commit()
        logger.info(
            "work_order.created id=%s number=%s (direct)",
            work_order.id,
            work_order_number,
        )
        return await self.get_work_order(work_order.id)

    # ── Create from budget ────────────────────────────────────────────────────

    async def create_from_budget(self, budget_id: uuid.UUID) -> WorkOrderResponse:
        """
        Creates WorkOrder + Tasks + TaskMaterials in a single transaction.
        Called from BudgetService.accept_and_create_work_order() after flush.

        Conversion rules:
        - BudgetLine(labor)    → Task(name=description, estimated_hours=quantity)
        - BudgetLine(material) → TaskMaterial on a shared "Materiales" task
        - BudgetLine(other)    → WorkOrder.other_lines_notes

        For each TaskMaterial:
        - unit_cost = snapshot of inventory_item.unit_cost_avg
        - stock_reserved += estimated_quantity (atomic UPDATE)
        """
        budget = await self._budget_repo.get_with_full_detail(budget_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Presupuesto no encontrado",
            )
        if budget.status.value != "accepted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El presupuesto debe estar en estado aceptado",
            )
        if budget.work_order_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este presupuesto ya tiene una obra asociada",
            )

        address = await self._resolve_work_order_address(budget)
        work_order_number = await self._repo.get_next_work_order_number()

        work_order = WorkOrder(
            work_order_number=work_order_number,
            customer_id=budget.customer_id,
            origin_budget_id=budget_id,
            status=WorkOrderStatus.DRAFT,
            address=address,
        )
        work_order = await self._repo.create(work_order)

        labor_lines = [l for l in budget.lines if l.line_type.value == "labor"]
        material_lines = [l for l in budget.lines if l.line_type.value == "material"]
        other_lines = [l for l in budget.lines if l.line_type.value == "other"]

        # Create tasks from labor lines
        tasks_by_line_id: dict[uuid.UUID, Task] = {}
        for i, line in enumerate(labor_lines):
            # unit_price: selling price per task (budget line subtotal with discounts)
            line_subtotal = line.quantity * line.unit_price
            if line.line_discount_pct > 0:
                line_subtotal *= 1 - line.line_discount_pct / 100
            task = Task(
                work_order_id=work_order.id,
                origin_budget_line_id=line.id,
                name=line.description,
                unit_price=line_subtotal.quantize(Decimal("0.01")),
                estimated_hours=line.quantity,
                sort_order=i,
            )
            task = await self._task_repo.create(task)
            tasks_by_line_id[line.id] = task

        # Determine target task for materials
        materials_task: Task | None = None
        if material_lines:
            if not labor_lines:
                materials_task = Task(
                    work_order_id=work_order.id,
                    name="Materiales",
                    description="Materiales del presupuesto",
                    sort_order=0,
                )
                materials_task = await self._task_repo.create(materials_task)
            else:
                materials_task = list(tasks_by_line_id.values())[0]

        # Create TaskMaterials and reserve stock
        for line in material_lines:
            if not line.inventory_item_id:
                continue
            item = await self._item_repo.get_by_id(line.inventory_item_id)
            if not item:
                continue

            unit_cost = item.unit_cost_avg if item.unit_cost_avg > 0 else item.unit_cost

            tm = TaskMaterial(
                task_id=materials_task.id,
                inventory_item_id=line.inventory_item_id,
                origin_budget_line_id=line.id,
                estimated_quantity=line.quantity,
                consumed_quantity=Decimal("0.0"),
                unit_cost=unit_cost,
            )
            await self._task_material_repo.create(tm)

            # Atomic stock_reserved update
            await self._session.execute(
                update(InventoryItem)
                .where(InventoryItem.id == line.inventory_item_id)
                .values(
                    stock_reserved=InventoryItem.stock_reserved + line.quantity
                )
            )

        # Append other lines as notes
        if other_lines:
            other_notes = "\n".join(f"- {l.description}" for l in other_lines)
            await self._repo.update(work_order, {"other_lines_notes": other_notes})

        # Link budget → work_order
        await self._budget_repo.update(budget, {"work_order_id": work_order.id})

        await self._session.commit()
        logger.info(
            "work_order.created id=%s number=%s from_budget=%s",
            work_order.id,
            work_order_number,
            budget_id,
        )
        return await self.get_work_order(work_order.id)

    # ── List / detail ─────────────────────────────────────────────────────────

    async def list_work_orders(
        self,
        q: str | None,
        customer_id: uuid.UUID | None,
        status_filter: str | None,
        skip: int,
        limit: int,
    ) -> WorkOrderListResponse:
        orders, total = await self._repo.search(
            query=q,
            customer_id=customer_id,
            status=status_filter,
            skip=skip,
            limit=limit,
        )
        return WorkOrderListResponse(
            items=[await self._build_summary(o) for o in orders],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_work_order(self, work_order_id: uuid.UUID) -> WorkOrderResponse:
        order = await self._repo.get_with_full_detail(work_order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra no encontrada",
            )
        return await self._build_response(order)

    async def update_work_order(
        self, work_order_id: uuid.UUID, data: WorkOrderUpdate
    ) -> WorkOrderResponse:
        order = await self._repo.get_by_id(work_order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra no encontrada",
            )
        if order.status == WorkOrderStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede modificar una obra cerrada",
            )
        await self._repo.update(order, data.model_dump(exclude_none=True))
        await self._session.commit()
        return await self.get_work_order(work_order_id)

    # ── Status transitions ────────────────────────────────────────────────────

    async def update_status(
        self, work_order_id: uuid.UUID, data: WorkOrderStatusUpdate
    ) -> WorkOrderResponse:
        order = await self._repo.get_by_id(work_order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra no encontrada",
            )
        self._validate_status_transition(order.status.value, data.status)

        update_data: dict = {"status": data.status}
        if data.notes:
            update_data["notes"] = (
                (order.notes or "") + f"\n[{data.status}] {data.notes}"
            ).strip()

        if data.status == "cancelled":
            await self._release_all_reserved_stock(work_order_id)

        await self._repo.update(order, update_data)
        await self._session.commit()
        logger.info(
            "work_order.status_changed id=%s %s→%s",
            work_order_id,
            order.status.value,
            data.status,
        )
        return await self.get_work_order(work_order_id)

    def _validate_status_transition(self, current: str, new: str) -> None:
        valid: dict[str, set[str]] = {
            "draft": {"active", "cancelled"},
            "active": {"pending_closure", "cancelled"},
            "pending_closure": {"closed", "active"},
            "closed": set(),
            "cancelled": set(),
        }
        if new not in valid.get(current, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede cambiar el estado de '{current}' a '{new}'",
            )

    # ── Task helpers ──────────────────────────────────────────────────────────

    async def _get_task_with_materials(self, task_id: uuid.UUID) -> Task:
        """Reload a task with its materials eagerly loaded."""
        from sqlalchemy.orm import selectinload

        result = await self._session.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.materials).selectinload(TaskMaterial.inventory_item),
                selectinload(Task.certification_items).selectinload(
                    CertificationItem.certification
                ),
            )
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada",
            )
        return task

    # ── Tasks ─────────────────────────────────────────────────────────────────

    async def add_task(
        self, work_order_id: uuid.UUID, data: TaskCreate
    ) -> TaskResponse:
        order = await self._repo.get_by_id(work_order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra no encontrada",
            )
        if order.status in (WorkOrderStatus.CLOSED, WorkOrderStatus.CANCELLED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pueden añadir tareas a una obra cerrada o cancelada",
            )
        task = Task(work_order_id=work_order_id, **data.model_dump())
        task = await self._task_repo.create(task)
        await self._session.commit()
        task = await self._get_task_with_materials(task.id)
        return self._build_task_response(task)

    async def update_task(
        self, work_order_id: uuid.UUID, task_id: uuid.UUID, data: TaskUpdate
    ) -> TaskResponse:
        task = await self._task_repo.get_by_id(task_id)
        if not task or task.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada en esta obra",
            )
        await self._task_repo.update(task, data.model_dump(exclude_none=True))
        await self._session.commit()
        task = await self._get_task_with_materials(task.id)
        return self._build_task_response(task)

    async def delete_task(
        self, work_order_id: uuid.UUID, task_id: uuid.UUID
    ) -> None:
        task = await self._task_repo.get_by_id(task_id)
        if not task or task.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada en esta obra",
            )
        if task.status != TaskStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden eliminar tareas en estado pendiente",
            )
        # Check no material has been consumed
        for mat in task.materials if hasattr(task, "materials") and task.materials else []:
            if mat.consumed_quantity > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede eliminar la tarea: tiene materiales consumidos",
                )
        await self._task_repo.delete(task)
        await self._session.commit()

    async def update_task_status(
        self,
        work_order_id: uuid.UUID,
        task_id: uuid.UUID,
        data: TaskStatusUpdate,
    ) -> WorkOrderResponse:
        task = await self._task_repo.get_by_id(task_id)
        if not task or task.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada en esta obra",
            )

        update_data: dict = {"status": data.status}
        if data.actual_hours is not None:
            update_data["actual_hours"] = data.actual_hours
        await self._task_repo.update(task, update_data)

        # Release stock_reserved if task cancelled
        if data.status == "cancelled":
            await self._release_task_reserved_stock(task_id)

        # Auto-transition work_order to pending_closure
        if data.status in ("completed", "cancelled"):
            all_done = await self._repo.check_all_tasks_completed(work_order_id)
            if all_done:
                order = await self._repo.get_by_id(work_order_id)
                if order and order.status == WorkOrderStatus.ACTIVE:
                    await self._repo.update(
                        order, {"status": WorkOrderStatus.PENDING_CLOSURE}
                    )
                    logger.info(
                        "work_order.auto_pending_closure id=%s", work_order_id
                    )

        await self._session.commit()
        return await self.get_work_order(work_order_id)

    # ── Add / remove materials ────────────────────────────────────────────────

    async def add_material(
        self, work_order_id: uuid.UUID, data: TaskMaterialCreate
    ) -> TaskResponse:
        """Adds a material to a task. Reserves stock."""
        task = await self._task_repo.get_by_id(data.task_id)
        if not task or task.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada en esta obra",
            )
        item = await self._item_repo.get_by_id(data.inventory_item_id)
        if not item or not item.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artículo de inventario no encontrado",
            )

        unit_cost = (
            data.unit_cost
            if data.unit_cost is not None
            else (item.unit_cost_avg if item.unit_cost_avg > 0 else item.unit_cost)
        )

        tm = TaskMaterial(
            task_id=data.task_id,
            inventory_item_id=data.inventory_item_id,
            estimated_quantity=data.estimated_quantity,
            consumed_quantity=Decimal("0.0"),
            unit_cost=unit_cost,
        )
        await self._task_material_repo.create(tm)

        # Reserve stock
        await self._session.execute(
            update(InventoryItem)
            .where(InventoryItem.id == data.inventory_item_id)
            .values(stock_reserved=InventoryItem.stock_reserved + data.estimated_quantity)
        )

        await self._session.commit()
        task = await self._get_task_with_materials(data.task_id)
        return self._build_task_response(task)

    async def remove_material(
        self, work_order_id: uuid.UUID, task_id: uuid.UUID, material_id: uuid.UUID
    ) -> TaskResponse:
        """Removes a material from a task. Releases reserved stock."""
        task = await self._task_repo.get_by_id(task_id)
        if not task or task.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada en esta obra",
            )
        tm = await self._task_material_repo.get_by_id(material_id)
        if not tm or tm.task_id != task_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material no encontrado en esta tarea",
            )
        if tm.consumed_quantity > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar un material que ya tiene consumo registrado",
            )

        # Release reserved stock
        pending = tm.estimated_quantity - tm.consumed_quantity
        if pending > 0:
            await self._session.execute(
                update(InventoryItem)
                .where(InventoryItem.id == tm.inventory_item_id)
                .values(
                    stock_reserved=InventoryItem.stock_reserved - pending
                )
            )

        await self._session.delete(tm)
        await self._session.commit()
        task = await self._get_task_with_materials(task_id)
        return self._build_task_response(task)

    # ── Material consumption ──────────────────────────────────────────────────

    async def consume_material(
        self,
        work_order_id: uuid.UUID,
        task_id: uuid.UUID,
        task_material_id: uuid.UUID,
        data: TaskMaterialConsume,
    ) -> TaskResponse:
        """
        Records real consumption for a task material.

        Rules:
        1. Task must be in_progress or completed
        2. Consumption above estimated is allowed (no error)
        3. Atomic stock update: delta = new_consumed - previous_consumed
           stock_current -= delta, stock_reserved -= delta
        4. Creates StockMovement(exit)
        """
        tm = await self._task_material_repo.get_by_id(task_material_id)
        if not tm or tm.task_id != task_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material no encontrado en esta tarea",
            )

        task = await self._task_repo.get_by_id(task_id)
        if not task or task.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada en esta obra",
            )
        if task.status not in (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede registrar consumo en tareas en progreso o completadas",
            )

        previous_consumed = tm.consumed_quantity
        delta = data.consumed_quantity - previous_consumed

        await self._task_material_repo.update(
            tm, {"consumed_quantity": data.consumed_quantity}
        )

        if delta != 0:
            await self._session.execute(
                update(InventoryItem)
                .where(InventoryItem.id == tm.inventory_item_id)
                .values(
                    stock_current=InventoryItem.stock_current - delta,
                    stock_reserved=InventoryItem.stock_reserved - delta,
                )
            )

            movement = StockMovement(
                inventory_item_id=tm.inventory_item_id,
                movement_type="exit",
                quantity=abs(delta),
                unit_cost=tm.unit_cost,
                reference_type="work_order",
                reference_id=work_order_id,
                notes=data.notes,
            )
            await self._movement_repo.create(movement)

        await self._session.commit()
        task = await self._get_task_with_materials(task.id)
        return self._build_task_response(task)

    # ── Purchase order links ──────────────────────────────────────────────────

    async def link_purchase_order(
        self, work_order_id: uuid.UUID, data: WorkOrderPurchaseOrderLink
    ) -> WorkOrderResponse:
        order = await self._repo.get_by_id(work_order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra no encontrada",
            )
        po = await self._purchase_order_repo.get_by_id(data.purchase_order_id)
        if not po:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )

        existing = await self._session.execute(
            select(WorkOrderPurchaseOrder)
            .where(WorkOrderPurchaseOrder.work_order_id == work_order_id)
            .where(
                WorkOrderPurchaseOrder.purchase_order_id == data.purchase_order_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este pedido ya está vinculado a la obra",
            )

        link = WorkOrderPurchaseOrder(
            work_order_id=work_order_id,
            purchase_order_id=data.purchase_order_id,
            notes=data.notes,
        )
        self._session.add(link)
        await self._session.flush()
        await self._session.commit()
        return await self.get_work_order(work_order_id)

    async def receive_purchase_order_from_work_order(
        self, work_order_id: uuid.UUID, purchase_order_id: uuid.UUID
    ) -> WorkOrderResponse:
        """Mark a linked PO as received and sync its lines to the work order's task materials.

        For each PO line with an inventory_item_id:
        - If a TaskMaterial for that item already exists in any task of this work order:
          estimated_quantity += received_quantity (and stock_reserved += same delta)
        - Otherwise: create a new TaskMaterial on the first active task and reserve stock.
        """
        from app.services.purchase_order import PurchaseOrderService

        # Validate the link exists
        link_result = await self._session.execute(
            select(WorkOrderPurchaseOrder)
            .where(WorkOrderPurchaseOrder.work_order_id == work_order_id)
            .where(WorkOrderPurchaseOrder.purchase_order_id == purchase_order_id)
        )
        if not link_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no vinculado a esta obra",
            )

        # Delegate to the PO service — this handles stock movements, PMP and status update.
        # receive_order commits the session internally.
        po_svc = PurchaseOrderService(self._session)
        received_po = await po_svc.receive_order(purchase_order_id)

        # Reload work order (session was committed by receive_order)
        order = await self._repo.get_with_full_detail(work_order_id)
        active_tasks = [t for t in (order.tasks or []) if t.status != "cancelled"]

        for line in received_po.lines:
            if line.inventory_item_id is None:
                continue

            item_id = line.inventory_item_id
            received_qty = line.quantity

            # Find a TaskMaterial for this item across all tasks of the work order
            existing_tm = None
            for task in active_tasks:
                for tm in task.materials:
                    if tm.inventory_item_id == item_id:
                        existing_tm = tm
                        break
                if existing_tm:
                    break

            if existing_tm is not None:
                # Increase estimated_quantity and reserve the additional stock
                await self._session.execute(
                    update(TaskMaterial)
                    .where(TaskMaterial.id == existing_tm.id)
                    .values(estimated_quantity=TaskMaterial.estimated_quantity + received_qty)
                )
                await self._session.execute(
                    update(InventoryItem)
                    .where(InventoryItem.id == item_id)
                    .values(stock_reserved=InventoryItem.stock_reserved + received_qty)
                )
            else:
                # Add as new material to the first active task
                if not active_tasks:
                    continue
                new_tm = TaskMaterial(
                    task_id=active_tasks[0].id,
                    inventory_item_id=item_id,
                    estimated_quantity=received_qty,
                    consumed_quantity=Decimal("0.0"),
                    unit_cost=line.unit_cost,
                )
                self._session.add(new_tm)
                await self._session.execute(
                    update(InventoryItem)
                    .where(InventoryItem.id == item_id)
                    .values(stock_reserved=InventoryItem.stock_reserved + received_qty)
                )

        await self._session.commit()
        order = await self._repo.get_with_full_detail(work_order_id)
        return await self._build_response(order)

    async def unlink_purchase_order(
        self, work_order_id: uuid.UUID, purchase_order_id: uuid.UUID
    ) -> None:
        result = await self._session.execute(
            select(WorkOrderPurchaseOrder)
            .where(WorkOrderPurchaseOrder.work_order_id == work_order_id)
            .where(WorkOrderPurchaseOrder.purchase_order_id == purchase_order_id)
        )
        link = result.scalar_one_or_none()
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vinculación no encontrada",
            )
        await self._session.delete(link)
        await self._session.commit()

    # ── Certifications ────────────────────────────────────────────────────────

    async def get_certifiable_tasks(
        self, work_order_id: uuid.UUID
    ) -> list[TaskResponse]:
        tasks = await self._task_repo.get_certifiable_tasks(work_order_id)
        return [self._build_task_response(t) for t in tasks]

    async def create_certification(
        self, work_order_id: uuid.UUID, data: CertificationCreate
    ) -> CertificationResponse:
        order = await self._repo.get_by_id(work_order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra no encontrada",
            )

        cert_number = await self._cert_repo.get_next_certification_number(
            order.work_order_number
        )
        cert = Certification(
            work_order_id=work_order_id,
            certification_number=cert_number,
            notes=data.notes,
        )
        cert = await self._cert_repo.create(cert)

        for item_data in data.items:
            task = await self._task_repo.get_by_id(item_data.task_id)
            if not task or task.work_order_id != work_order_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tarea {item_data.task_id} no encontrada",
                )
            if task.status != TaskStatus.COMPLETED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La tarea '{task.name}' debe estar completada para certificarla",
                )

            if item_data.amount is not None:
                amount = item_data.amount.quantize(Decimal("0.01"))
            else:
                amount = await self._calculate_task_amount(task)
            cert_item = CertificationItem(
                certification_id=cert.id,
                task_id=task.id,
                amount=amount,
                notes=item_data.notes,
            )
            self._session.add(cert_item)

        await self._session.flush()
        await self._session.commit()

        refreshed = await self._cert_repo.get_with_items(cert.id)
        return self._build_certification_response(refreshed)

    async def issue_certification(
        self, work_order_id: uuid.UUID, cert_id: uuid.UUID
    ) -> CertificationResponse:
        cert = await self._cert_repo.get_with_items(cert_id)
        if not cert or cert.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificación no encontrada",
            )
        if cert.status.value != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden emitir certificaciones en borrador",
            )
        if not cert.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La certificación no tiene tareas",
            )

        await self._cert_repo.update(cert, {"status": "issued"})
        await self._session.commit()
        refreshed = await self._cert_repo.get_with_items(cert_id)
        return self._build_certification_response(refreshed)

    async def delete_certification(
        self, work_order_id: uuid.UUID, cert_id: uuid.UUID
    ) -> None:
        cert = await self._cert_repo.get_by_id(cert_id)
        if not cert or cert.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificación no encontrada",
            )
        if cert.status.value != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden eliminar certificaciones en borrador",
            )
        await self._cert_repo.delete(cert)
        await self._session.commit()

    # ── KPIs ──────────────────────────────────────────────────────────────────

    async def get_kpis(self, work_order_id: uuid.UUID) -> WorkOrderKPIs:
        order = await self._repo.get_with_full_detail(work_order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra no encontrada",
            )
        return self._compute_kpis(order)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _compute_kpis(self, order: WorkOrder) -> WorkOrderKPIs:
        total_tasks = len(order.tasks)
        completed_tasks = sum(
            1 for t in order.tasks if t.status == TaskStatus.COMPLETED
        )
        progress_pct = (
            Decimal(completed_tasks) / Decimal(total_tasks) * 100
            if total_tasks > 0
            else Decimal("0.0")
        )

        estimated_hours = sum(
            (t.estimated_hours or Decimal("0.0")) for t in order.tasks
        )
        actual_hours = sum(
            (t.actual_hours or Decimal("0.0")) for t in order.tasks
        )
        hours_deviation = (
            (actual_hours - estimated_hours) / estimated_hours * 100
            if estimated_hours > 0
            else Decimal("0.0")
        )

        all_materials = [m for t in order.tasks for m in (t.materials or [])]
        actual_cost = sum(
            (m.consumed_quantity * m.unit_cost for m in all_materials), Decimal("0.0")
        )
        budget_cost = sum(
            (m.estimated_quantity * m.unit_cost for m in all_materials), Decimal("0.0")
        )
        cost_deviation = (
            (actual_cost - budget_cost) / budget_cost * 100
            if budget_cost > 0
            else Decimal("0.0")
        )

        # Budget total (pre-tax, with discounts)
        budget = order.origin_budget
        budget_total = Decimal("0.0")
        if budget and budget.lines:
            for line in budget.lines:
                line_subtotal = line.quantity * line.unit_price
                if line.line_discount_pct > 0:
                    line_subtotal *= 1 - line.line_discount_pct / 100
                budget_total += line_subtotal
            if budget.discount_pct > 0:
                budget_total *= 1 - budget.discount_pct / 100

        total_certified = Decimal("0.0")
        total_invoiced = Decimal("0.0")
        for c in (order.certifications or []):
            if c.status.value in ("issued", "invoiced"):
                cert_amount = sum(
                    (i.amount for i in (c.items or [])), Decimal("0.0")
                )
                total_certified += cert_amount
                if c.status.value == "invoiced":
                    total_invoiced += cert_amount

        pending_to_certify = budget_total - total_certified
        margin_real = (
            (budget_total - actual_cost) / budget_total * 100
            if budget_total > 0
            else Decimal("0.0")
        )

        total_pos = len(order.purchase_order_links or [])
        pending_pos = sum(
            1
            for link in (order.purchase_order_links or [])
            if link.purchase_order
            and link.purchase_order.status == "pending"
        )

        return WorkOrderKPIs(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            progress_pct=progress_pct.quantize(Decimal("0.1")),
            estimated_hours=estimated_hours,
            actual_hours=actual_hours,
            hours_deviation_pct=hours_deviation.quantize(Decimal("0.1")),
            budget_cost=budget_cost,
            actual_cost=actual_cost,
            cost_deviation_pct=cost_deviation.quantize(Decimal("0.1")),
            total_task_materials=len(all_materials),
            fully_consumed_materials=sum(
                1
                for m in all_materials
                if m.consumed_quantity >= m.estimated_quantity
            ),
            pending_materials=sum(
                1
                for m in all_materials
                if m.consumed_quantity < m.estimated_quantity
            ),
            budget_total=budget_total.quantize(Decimal("0.01")),
            total_certified=total_certified.quantize(Decimal("0.01")),
            total_invoiced=total_invoiced.quantize(Decimal("0.01")),
            pending_to_certify=pending_to_certify.quantize(Decimal("0.01")),
            margin_real_pct=margin_real.quantize(Decimal("0.1")),
            total_purchase_orders=total_pos,
            pending_purchase_orders=pending_pos,
        )

    async def _build_summary(self, order: WorkOrder) -> WorkOrderSummary:
        total_tasks = len(order.tasks) if order.tasks else 0
        completed_tasks = (
            sum(1 for t in order.tasks if t.status == TaskStatus.COMPLETED)
            if order.tasks
            else 0
        )
        progress_pct = (
            Decimal(completed_tasks) / Decimal(total_tasks) * 100
            if total_tasks > 0
            else Decimal("0.0")
        )

        # Budget total without tax for summary
        budget = order.origin_budget
        budget_total = Decimal("0.0")
        if budget and budget.lines:
            for line in budget.lines:
                line_subtotal = line.quantity * line.unit_price
                if line.line_discount_pct > 0:
                    line_subtotal *= 1 - line.line_discount_pct / 100
                budget_total += line_subtotal
            if budget.discount_pct > 0:
                budget_total *= 1 - budget.discount_pct / 100

        all_materials = [
            m for t in (order.tasks or []) for m in (t.materials or [])
        ]
        actual_cost = sum(
            (m.consumed_quantity * m.unit_cost for m in all_materials), Decimal("0.0")
        )

        total_certified = Decimal("0.0")
        for c in (order.certifications or []):
            if c.status.value in ("issued", "invoiced"):
                total_certified += sum(
                    (i.amount for i in (c.items or [])), Decimal("0.0")
                )

        customer = order.customer
        return WorkOrderSummary(
            id=order.id,
            work_order_number=order.work_order_number,
            customer_id=order.customer_id,
            customer_name=customer.name if customer else "",
            customer_email=customer.email if customer else None,
            customer_phone=customer.phone if customer else None,
            origin_budget_id=order.origin_budget_id,
            budget_number=budget.budget_number if budget else None,
            status=order.status.value,
            address=order.address,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            progress_pct=progress_pct.quantize(Decimal("0.1")),
            budget_total=budget_total.quantize(Decimal("0.01")),
            total_certified=total_certified.quantize(Decimal("0.01")),
            actual_cost=actual_cost.quantize(Decimal("0.01")),
            created_at=order.created_at,
        )

    def _build_po_link_response(self, link: WorkOrderPurchaseOrder) -> LinkedPurchaseOrderResponse:
        from app.schemas.work_order import LinkedPOLineResponse

        po = link.purchase_order
        supplier = po.supplier
        total_amount = sum(
            (line.subtotal for line in (po.lines or [])),
            Decimal("0.0"),
        )
        lines = [
            LinkedPOLineResponse(
                inventory_item_name=(
                    line.inventory_item.name if line.inventory_item else None
                ),
                description=line.description,
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                subtotal=line.subtotal,
            )
            for line in (po.lines or [])
        ]
        return LinkedPurchaseOrderResponse(
            id=link.id,
            purchase_order_id=link.purchase_order_id,
            supplier_id=po.supplier_id,
            order_number=po.order_number,
            supplier_name=supplier.name if supplier else "—",
            supplier_email=supplier.email if supplier else None,
            supplier_phone=supplier.phone if supplier else None,
            status=po.status,
            order_date=str(po.order_date),
            expected_date=str(po.expected_date) if po.expected_date else None,
            total_amount=total_amount,
            notes=link.notes,
            lines=lines,
        )

    async def _build_response(self, order: WorkOrder) -> WorkOrderResponse:
        summary = await self._build_summary(order)
        kpis = self._compute_kpis(order)
        po_links = [
            self._build_po_link_response(link)
            for link in (order.purchase_order_links or [])
            if link.purchase_order
        ]
        return WorkOrderResponse(
            **summary.model_dump(),
            other_lines_notes=order.other_lines_notes,
            notes=order.notes,
            assigned_to=order.assigned_to,
            tasks=[self._build_task_response(t) for t in (order.tasks or [])],
            certifications=[
                self._build_certification_response(c)
                for c in (order.certifications or [])
            ],
            purchase_order_links=po_links,
            delivery_notes=[
                self._build_delivery_note_response(dn)
                for dn in (order.delivery_notes or [])
            ],
            kpis=kpis,
            updated_at=order.updated_at,
        )

    def _build_task_response(self, task: Task) -> TaskResponse:
        materials = []
        estimated_cost = Decimal("0.0")
        actual_cost = Decimal("0.0")

        for m in (task.materials or []):
            item_name = ""
            item_unit = ""
            if hasattr(m, "inventory_item") and m.inventory_item:
                item_name = m.inventory_item.name
                item_unit = m.inventory_item.unit
            m_estimated_cost = m.estimated_quantity * m.unit_cost
            m_actual_cost = m.consumed_quantity * m.unit_cost
            estimated_cost += m_estimated_cost
            actual_cost += m_actual_cost
            materials.append(
                TaskMaterialResponse(
                    id=m.id,
                    task_id=m.task_id,
                    inventory_item_id=m.inventory_item_id,
                    inventory_item_name=item_name,
                    inventory_item_unit=item_unit,
                    estimated_quantity=m.estimated_quantity,
                    consumed_quantity=m.consumed_quantity,
                    pending_quantity=max(
                        m.estimated_quantity - m.consumed_quantity,
                        Decimal("0.0"),
                    ),
                    unit_cost=m.unit_cost,
                    estimated_cost=m_estimated_cost,
                    actual_cost=m_actual_cost,
                )
            )

        # Check if task is certified in an issued/invoiced certification
        is_certified = False
        certification_id = None
        if hasattr(task, "certification_items"):
            for ci in (task.certification_items or []):
                if hasattr(ci, "certification") and ci.certification:
                    if ci.certification.status.value in ("issued", "invoiced"):
                        is_certified = True
                        certification_id = ci.certification.id
                        break

        return TaskResponse(
            id=task.id,
            work_order_id=task.work_order_id,
            origin_budget_line_id=task.origin_budget_line_id,
            name=task.name,
            description=task.description,
            status=task.status.value,
            sort_order=task.sort_order,
            unit_price=task.unit_price,
            estimated_hours=task.estimated_hours,
            actual_hours=task.actual_hours,
            materials=materials,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
            is_certified=is_certified,
            certification_id=certification_id,
            created_at=task.created_at,
        )

    def _build_certification_response(
        self, cert: Certification
    ) -> CertificationResponse:
        items = []
        total = Decimal("0.0")
        for ci in (cert.items or []):
            task = ci.task if hasattr(ci, "task") else None
            items.append(
                CertificationItemResponse(
                    id=ci.id,
                    task_id=ci.task_id,
                    task_name=task.name if task else "",
                    task_status=task.status.value if task else "",
                    amount=ci.amount,
                    notes=ci.notes,
                )
            )
            total += ci.amount
        return CertificationResponse(
            id=cert.id,
            work_order_id=cert.work_order_id,
            certification_number=cert.certification_number,
            status=cert.status.value,
            notes=cert.notes,
            invoice_id=cert.invoice_id,
            items=items,
            total_amount=total,
            created_at=cert.created_at,
            updated_at=cert.updated_at,
        )

    async def _calculate_task_amount(self, task: Task) -> Decimal:
        """
        Calculates the certifiable amount for a task.
        Priority: task.unit_price > budget line subtotal > 0
        """
        if task.unit_price is not None:
            return task.unit_price.quantize(Decimal("0.01"))

        if not task.origin_budget_line_id:
            return Decimal("0.00")

        line = await self._budget_line_repo.get_by_id(task.origin_budget_line_id)
        if not line:
            return Decimal("0.00")

        subtotal = line.quantity * line.unit_price
        if line.line_discount_pct > 0:
            subtotal *= 1 - line.line_discount_pct / 100

        budget = await self._budget_repo.get_by_id(line.budget_id)
        if budget and budget.discount_pct > 0:
            subtotal *= 1 - budget.discount_pct / 100

        return subtotal.quantize(Decimal("0.01"))

    async def _resolve_work_order_address(self, budget) -> str | None:
        """Gets the work address from the site visit or customer."""
        if budget.site_visit_id:
            visit = await self._visit_repo.get_by_id(budget.site_visit_id)
            if visit and getattr(visit, "address_text", None):
                return visit.address_text

        customer = await self._customer_repo.get_by_id(budget.customer_id)
        if customer:
            # Load addresses lazily if needed
            from sqlalchemy.orm import selectinload
            from sqlalchemy import select as sa_select
            from app.models.customer import Customer, CustomerAddress

            result = await self._session.execute(
                sa_select(CustomerAddress)
                .where(CustomerAddress.customer_id == customer.id)
                .order_by(CustomerAddress.is_default.desc())
            )
            addresses = list(result.scalars().all())
            if addresses:
                service = next(
                    (a for a in addresses if a.address_type.value == "service"),
                    addresses[0],
                )
                return f"{service.street}, {service.city}"
        return None

    async def _release_all_reserved_stock(
        self, work_order_id: uuid.UUID
    ) -> None:
        """Releases stock_reserved for all pending/in_progress TaskMaterials."""
        result = await self._session.execute(
            select(TaskMaterial)
            .join(Task)
            .where(Task.work_order_id == work_order_id)
            .where(
                Task.status.in_(
                    [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]
                )
            )
        )
        materials = list(result.scalars().all())
        for tm in materials:
            pending = tm.estimated_quantity - tm.consumed_quantity
            if pending > 0:
                await self._session.execute(
                    update(InventoryItem)
                    .where(InventoryItem.id == tm.inventory_item_id)
                    .values(
                        stock_reserved=InventoryItem.stock_reserved - pending
                    )
                )

    async def _release_task_reserved_stock(
        self, task_id: uuid.UUID
    ) -> None:
        """Releases stock_reserved for all pending TaskMaterials of a task."""
        result = await self._session.execute(
            select(TaskMaterial).where(TaskMaterial.task_id == task_id)
        )
        materials = list(result.scalars().all())
        for tm in materials:
            pending = tm.estimated_quantity - tm.consumed_quantity
            if pending > 0:
                await self._session.execute(
                    update(InventoryItem)
                    .where(InventoryItem.id == tm.inventory_item_id)
                    .values(
                        stock_reserved=InventoryItem.stock_reserved - pending
                    )
                )

    # ── Delivery Notes ────────────────────────────────────────────────────────

    async def create_delivery_note(
        self, work_order_id: uuid.UUID, data: DeliveryNoteCreate
    ) -> DeliveryNoteResponse:
        order = await self._repo.get_by_id(work_order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra no encontrada",
            )

        number = await self._delivery_note_repo.get_next_delivery_note_number(
            order.work_order_number
        )
        note = DeliveryNote(
            work_order_id=work_order_id,
            delivery_note_number=number,
            status=DeliveryNoteStatus.DRAFT,
            delivery_date=str(data.delivery_date),
            requested_by=data.requested_by,
            notes=data.notes,
        )
        note = await self._delivery_note_repo.create(note)

        for idx, item_data in enumerate(data.items):
            item = DeliveryNoteItem(
                delivery_note_id=note.id,
                line_type=item_data.line_type,
                description=item_data.description,
                inventory_item_id=item_data.inventory_item_id,
                quantity=item_data.quantity,
                unit=item_data.unit,
                unit_price=item_data.unit_price,
                sort_order=item_data.sort_order if item_data.sort_order else idx,
            )
            await self._delivery_note_item_repo.create(item)

        await self._session.commit()
        logger.info(
            "delivery_note.created id=%s number=%s", note.id, number
        )
        refreshed = await self._delivery_note_repo.get_with_items(note.id)
        return self._build_delivery_note_response(refreshed)

    async def list_delivery_notes(
        self, work_order_id: uuid.UUID
    ) -> list[DeliveryNoteResponse]:
        order = await self._repo.get_by_id(work_order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obra no encontrada",
            )
        notes = await self._delivery_note_repo.list_by_work_order(work_order_id)
        return [self._build_delivery_note_response(n) for n in notes]

    async def get_delivery_note(
        self, work_order_id: uuid.UUID, delivery_note_id: uuid.UUID
    ) -> DeliveryNoteResponse:
        note = await self._delivery_note_repo.get_with_items(delivery_note_id)
        if not note or note.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Albarán no encontrado en esta obra",
            )
        return self._build_delivery_note_response(note)

    async def update_delivery_note(
        self,
        work_order_id: uuid.UUID,
        delivery_note_id: uuid.UUID,
        data: DeliveryNoteUpdate,
    ) -> DeliveryNoteResponse:
        note = await self._delivery_note_repo.get_with_items(delivery_note_id)
        if not note or note.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Albarán no encontrado en esta obra",
            )
        if note.status != DeliveryNoteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden editar albaranes en borrador",
            )

        update_fields: dict = {}
        if data.delivery_date is not None:
            update_fields["delivery_date"] = str(data.delivery_date)
        if data.requested_by is not None:
            update_fields["requested_by"] = data.requested_by
        if data.notes is not None:
            update_fields["notes"] = data.notes

        if update_fields:
            await self._delivery_note_repo.update(note, update_fields)

        if data.items is not None:
            # Replace all items
            for existing in (note.items or []):
                await self._delivery_note_item_repo.delete(existing)
            for idx, item_data in enumerate(data.items):
                item = DeliveryNoteItem(
                    delivery_note_id=note.id,
                    line_type=item_data.line_type,
                    description=item_data.description,
                    inventory_item_id=item_data.inventory_item_id,
                    quantity=item_data.quantity,
                    unit=item_data.unit,
                    unit_price=item_data.unit_price,
                    sort_order=item_data.sort_order if item_data.sort_order else idx,
                )
                await self._delivery_note_item_repo.create(item)

        await self._session.commit()
        refreshed = await self._delivery_note_repo.get_with_items(note.id)
        return self._build_delivery_note_response(refreshed)

    async def issue_delivery_note(
        self, work_order_id: uuid.UUID, delivery_note_id: uuid.UUID
    ) -> DeliveryNoteResponse:
        note = await self._delivery_note_repo.get_with_items(delivery_note_id)
        if not note or note.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Albarán no encontrado en esta obra",
            )
        if note.status != DeliveryNoteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El albarán ya está emitido",
            )
        if not note.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El albarán debe tener al menos una línea para poder emitirse",
            )
        await self._delivery_note_repo.update(
            note, {"status": DeliveryNoteStatus.ISSUED}
        )
        await self._session.commit()
        logger.info("delivery_note.issued id=%s", delivery_note_id)
        refreshed = await self._delivery_note_repo.get_with_items(note.id)
        return self._build_delivery_note_response(refreshed)

    async def delete_delivery_note(
        self, work_order_id: uuid.UUID, delivery_note_id: uuid.UUID
    ) -> None:
        note = await self._delivery_note_repo.get_by_id(delivery_note_id)
        if not note or note.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Albarán no encontrado en esta obra",
            )
        if note.status != DeliveryNoteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden eliminar albaranes en borrador",
            )
        await self._delivery_note_repo.delete(note)
        await self._session.commit()
        logger.info("delivery_note.deleted id=%s", delivery_note_id)

    def _build_delivery_note_response(
        self, note: DeliveryNote
    ) -> DeliveryNoteResponse:
        items = []
        total = Decimal("0.0")
        for item in (note.items or []):
            subtotal = item.quantity * item.unit_price
            total += subtotal
            inv_name = None
            if hasattr(item, "inventory_item") and item.inventory_item:
                inv_name = item.inventory_item.name
            items.append(
                DeliveryNoteItemResponse(
                    id=item.id,
                    delivery_note_id=item.delivery_note_id,
                    line_type=item.line_type.value,
                    description=item.description,
                    inventory_item_id=item.inventory_item_id,
                    inventory_item_name=inv_name,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_price=item.unit_price,
                    subtotal=subtotal,
                    sort_order=item.sort_order,
                )
            )
        return DeliveryNoteResponse(
            id=note.id,
            work_order_id=note.work_order_id,
            delivery_note_number=note.delivery_note_number,
            status=note.status.value,
            delivery_date=note.delivery_date,
            requested_by=note.requested_by,
            notes=note.notes,
            items=items,
            total_amount=total,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )

    # ── Delivery Note PDF / Email / WhatsApp ──────────────────────────────────

    async def generate_delivery_note_pdf(
        self, work_order_id: uuid.UUID, delivery_note_id: uuid.UUID
    ) -> bytes:
        from weasyprint import HTML

        from app.core.config import settings
        from app.repositories.company_settings import CompanySettingsRepository
        from app.utils.pdf_renderer import render_delivery_note_pdf_html

        note = await self._delivery_note_repo.get_with_items(delivery_note_id)
        if not note or note.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Albarán no encontrado en esta obra",
            )
        order = await self._repo.get_by_id(work_order_id)
        customer = await self._customer_repo.get_by_id(order.customer_id)
        company = await CompanySettingsRepository(self._session).get()

        total_amount = sum(
            (item.quantity * item.unit_price for item in (note.items or [])),
            Decimal("0.0"),
        )

        html = render_delivery_note_pdf_html(
            note=note,
            work_order=order,
            company=company,
            customer=customer,
            total_amount=total_amount,
        )
        pdf_bytes = HTML(string=html).write_pdf()

        upload_dir = Path(settings.UPLOAD_DIR) / "delivery_notes" / str(delivery_note_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        (upload_dir / f"{note.delivery_note_number}.pdf").write_bytes(pdf_bytes)

        logger.info(
            "delivery_note.pdf_generated id=%s number=%s",
            delivery_note_id,
            note.delivery_note_number,
        )
        return pdf_bytes

    async def send_delivery_note_email(
        self,
        work_order_id: uuid.UUID,
        delivery_note_id: uuid.UUID,
        data: SendDocumentEmail,
    ) -> None:
        from app.repositories.company_settings import CompanySettingsRepository
        from app.utils.email_sender import send_email_with_attachment

        note = await self._delivery_note_repo.get_with_items(delivery_note_id)
        if not note or note.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Albarán no encontrado en esta obra",
            )
        order = await self._repo.get_by_id(work_order_id)
        company = await CompanySettingsRepository(self._session).get()

        pdf_bytes = await self.generate_delivery_note_pdf(work_order_id, delivery_note_id)

        subject = data.subject or (
            f"Albarán {note.delivery_note_number} — {company.company_name}"
        )
        body = data.message or (
            f"<p>Estimado/a cliente,</p>"
            f"<p>Le adjuntamos el albarán <strong>{note.delivery_note_number}</strong> "
            f"correspondiente a la obra <strong>{order.work_order_number}</strong>.</p>"
            f"<p>Fecha de entrega: {note.delivery_date}</p>"
            f"<br><p>Atentamente,<br><strong>{company.company_name}</strong></p>"
        )

        await send_email_with_attachment(
            to_email=data.to_email,
            subject=subject,
            body_html=body,
            attachment_bytes=pdf_bytes,
            attachment_filename=f"{note.delivery_note_number}.pdf",
        )
        logger.info(
            "delivery_note.email_sent id=%s to=%s", delivery_note_id, data.to_email
        )

    async def get_delivery_note_whatsapp_link(
        self,
        work_order_id: uuid.UUID,
        delivery_note_id: uuid.UUID,
        phone: str | None,
    ) -> WhatsAppLinkResponse:
        from app.repositories.company_settings import CompanySettingsRepository

        note = await self._delivery_note_repo.get_with_items(delivery_note_id)
        if not note or note.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Albarán no encontrado en esta obra",
            )
        order = await self._repo.get_by_id(work_order_id)
        company = await CompanySettingsRepository(self._session).get()

        if not phone:
            customer = await self._customer_repo.get_by_id(order.customer_id)
            phone = customer.phone if customer else None

        if not phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay número de teléfono disponible para el enlace de WhatsApp",
            )

        normalized = _normalize_phone_es(phone)
        total = sum(i.quantity * i.unit_price for i in (note.items or []))
        text = (
            f"Estimado/a cliente, le enviamos el albarán "
            f"*{note.delivery_note_number}* "
            f"de la obra *{order.work_order_number}*.\n"
            f"Fecha de entrega: {note.delivery_date}\n"
            f"Total: {float(total):,.2f} €\n\n"
            f"— {company.company_name}"
        )
        import urllib.parse
        url = f"https://wa.me/{normalized}?text={urllib.parse.quote(text)}"
        return WhatsAppLinkResponse(url=url, phone=normalized)

    # ── Certification PDF / Email / WhatsApp ──────────────────────────────────

    async def generate_certification_pdf(
        self, work_order_id: uuid.UUID, cert_id: uuid.UUID
    ) -> bytes:
        from weasyprint import HTML

        from app.core.config import settings
        from app.repositories.company_settings import CompanySettingsRepository
        from app.utils.pdf_renderer import render_certification_pdf_html

        cert = await self._cert_repo.get_with_items(cert_id)
        if not cert or cert.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificación no encontrada en esta obra",
            )
        order = await self._repo.get_by_id(work_order_id)
        customer = await self._customer_repo.get_by_id(order.customer_id)
        company = await CompanySettingsRepository(self._session).get()

        total_amount = sum(
            (item.amount for item in (cert.items or [])),
            Decimal("0.0"),
        )

        html = render_certification_pdf_html(
            cert=cert,
            work_order=order,
            company=company,
            customer=customer,
            total_amount=total_amount,
        )
        pdf_bytes = HTML(string=html).write_pdf()

        upload_dir = Path(settings.UPLOAD_DIR) / "certifications" / str(cert_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        (upload_dir / f"{cert.certification_number}.pdf").write_bytes(pdf_bytes)

        logger.info(
            "certification.pdf_generated id=%s number=%s",
            cert_id,
            cert.certification_number,
        )
        return pdf_bytes

    async def send_certification_email(
        self,
        work_order_id: uuid.UUID,
        cert_id: uuid.UUID,
        data: SendDocumentEmail,
    ) -> None:
        from app.repositories.company_settings import CompanySettingsRepository
        from app.utils.email_sender import send_email_with_attachment

        cert = await self._cert_repo.get_with_items(cert_id)
        if not cert or cert.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificación no encontrada en esta obra",
            )
        order = await self._repo.get_by_id(work_order_id)
        company = await CompanySettingsRepository(self._session).get()

        pdf_bytes = await self.generate_certification_pdf(work_order_id, cert_id)

        subject = data.subject or (
            f"Certificación {cert.certification_number} — {company.company_name}"
        )
        body = data.message or (
            f"<p>Estimado/a cliente,</p>"
            f"<p>Le adjuntamos la certificación de avance "
            f"<strong>{cert.certification_number}</strong> "
            f"correspondiente a la obra <strong>{order.work_order_number}</strong>.</p>"
            f"<p>Le rogamos revise el documento y confirme su conformidad.</p>"
            f"<br><p>Atentamente,<br><strong>{company.company_name}</strong></p>"
        )

        await send_email_with_attachment(
            to_email=data.to_email,
            subject=subject,
            body_html=body,
            attachment_bytes=pdf_bytes,
            attachment_filename=f"{cert.certification_number}.pdf",
        )
        logger.info(
            "certification.email_sent id=%s to=%s", cert_id, data.to_email
        )

    async def get_certification_whatsapp_link(
        self,
        work_order_id: uuid.UUID,
        cert_id: uuid.UUID,
        phone: str | None,
    ) -> WhatsAppLinkResponse:
        from app.repositories.company_settings import CompanySettingsRepository

        cert = await self._cert_repo.get_with_items(cert_id)
        if not cert or cert.work_order_id != work_order_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificación no encontrada en esta obra",
            )
        order = await self._repo.get_by_id(work_order_id)
        company = await CompanySettingsRepository(self._session).get()

        if not phone:
            customer = await self._customer_repo.get_by_id(order.customer_id)
            phone = customer.phone if customer else None

        if not phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay número de teléfono disponible para el enlace de WhatsApp",
            )

        normalized = _normalize_phone_es(phone)
        total = sum(item.amount for item in (cert.items or []))
        text = (
            f"Estimado/a cliente, le enviamos la certificación de avance "
            f"*{cert.certification_number}* "
            f"de la obra *{order.work_order_number}*.\n"
            f"Importe certificado: {float(total):,.2f} €\n"
            f"Le rogamos confirme su conformidad.\n\n"
            f"— {company.company_name}"
        )
        import urllib.parse
        url = f"https://wa.me/{normalized}?text={urllib.parse.quote(text)}"
        return WhatsAppLinkResponse(url=url, phone=normalized)


def _normalize_phone_es(phone: str) -> str:
    """
    Normalizes a Spanish phone number to the format required by wa.me (digits only,
    with country code). Examples:
        +34 600 123 456  → 34600123456
        0034600123456    → 34600123456
        600 123 456      → 34600123456
    """
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0034"):
        digits = digits[2:]
    elif digits.startswith("34") and len(digits) == 11:
        pass  # already has country code
    elif digits.startswith(("6", "7", "9")) and len(digits) == 9:
        digits = "34" + digits
    return digits
