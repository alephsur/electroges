"""Repositories for the WorkOrder module."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.work_order import (
    Certification,
    CertificationItem,
    DeliveryNote,
    DeliveryNoteItem,
    Task,
    TaskMaterial,
    WorkOrder,
    WorkOrderPurchaseOrder,
)
from app.repositories.base import BaseRepository


class WorkOrderRepository(BaseRepository[WorkOrder]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(WorkOrder, session, tenant_id)

    async def get_next_work_order_number(self) -> str:
        year = datetime.now().year
        stmt = select(func.count(WorkOrder.id)).where(
            WorkOrder.work_order_number.like(f"OBRA-{year}-%")
        )
        if self.tenant_id is not None:
            stmt = stmt.where(WorkOrder.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        return f"OBRA-{year}-{(count + 1):04d}"

    async def search(
        self,
        query: str | None,
        customer_id: uuid.UUID | None,
        status: str | None,
        skip: int,
        limit: int,
    ) -> tuple[list[WorkOrder], int]:
        from app.models.customer import Customer
        from app.models.budget import Budget

        stmt = select(WorkOrder).options(
            selectinload(WorkOrder.customer),
            selectinload(WorkOrder.origin_budget).selectinload(Budget.lines),
            selectinload(WorkOrder.tasks).selectinload(Task.materials),
            selectinload(WorkOrder.certifications).selectinload(Certification.items),
        )
        count_stmt = select(func.count()).select_from(WorkOrder)

        if self.tenant_id is not None:
            stmt = stmt.where(WorkOrder.tenant_id == self.tenant_id)
            count_stmt = count_stmt.where(WorkOrder.tenant_id == self.tenant_id)

        if customer_id is not None:
            stmt = stmt.where(WorkOrder.customer_id == customer_id)
            count_stmt = count_stmt.where(WorkOrder.customer_id == customer_id)

        if status is not None:
            stmt = stmt.where(WorkOrder.status == status)
            count_stmt = count_stmt.where(WorkOrder.status == status)

        if query:
            search = f"%{query}%"
            stmt = stmt.join(Customer, WorkOrder.customer_id == Customer.id).where(
                or_(
                    WorkOrder.work_order_number.ilike(search),
                    Customer.name.ilike(search),
                    WorkOrder.address.ilike(search),
                )
            )
            count_stmt = count_stmt.join(
                Customer, WorkOrder.customer_id == Customer.id
            ).where(
                or_(
                    WorkOrder.work_order_number.ilike(search),
                    Customer.name.ilike(search),
                    WorkOrder.address.ilike(search),
                )
            )

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(WorkOrder.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        orders = list(result.scalars().all())
        return orders, total

    async def get_with_full_detail(
        self, work_order_id: uuid.UUID
    ) -> WorkOrder | None:
        from app.models.budget import Budget
        from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine

        stmt = (
            select(WorkOrder)
            .options(
                selectinload(WorkOrder.customer),
                selectinload(WorkOrder.origin_budget).selectinload(Budget.lines),
                selectinload(WorkOrder.tasks).selectinload(
                    Task.materials
                ).selectinload(TaskMaterial.inventory_item),
                selectinload(WorkOrder.tasks).selectinload(
                    Task.certification_items
                ).selectinload(CertificationItem.certification),
                selectinload(WorkOrder.certifications).selectinload(
                    Certification.items
                ).selectinload(CertificationItem.task),
                selectinload(WorkOrder.purchase_order_links).selectinload(
                    WorkOrderPurchaseOrder.purchase_order
                ).selectinload(PurchaseOrder.supplier),
                selectinload(WorkOrder.purchase_order_links).selectinload(
                    WorkOrderPurchaseOrder.purchase_order
                ).selectinload(PurchaseOrder.lines).selectinload(
                    PurchaseOrderLine.inventory_item
                ),
                selectinload(WorkOrder.delivery_notes).selectinload(
                    DeliveryNote.items
                ).selectinload(DeliveryNoteItem.inventory_item),
            )
            .where(WorkOrder.id == work_order_id)
        )
        stmt = self._tenant_filter(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_customer(self, customer_id: uuid.UUID) -> list[WorkOrder]:
        stmt = (
            select(WorkOrder)
            .where(WorkOrder.customer_id == customer_id)
            .order_by(WorkOrder.created_at.desc())
        )
        stmt = self._tenant_filter(stmt)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def check_all_tasks_completed(self, work_order_id: uuid.UUID) -> bool:
        from app.models.work_order import TaskStatus

        result = await self.session.execute(
            select(
                func.sum(
                    case(
                        (Task.status == TaskStatus.COMPLETED.value, 1),
                        else_=0,
                    )
                ).label("completed"),
                func.sum(
                    case(
                        (
                            Task.status.notin_(
                                [
                                    TaskStatus.COMPLETED.value,
                                    TaskStatus.CANCELLED.value,
                                ]
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("pending"),
            ).where(Task.work_order_id == work_order_id)
        )
        row = result.one()
        completed = row.completed or 0
        pending = row.pending or 0
        return completed > 0 and pending == 0


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(Task, session, tenant_id)

    async def get_certifiable_tasks(
        self, work_order_id: uuid.UUID
    ) -> list[Task]:
        """Tareas completadas que no están en ninguna certificación issued/invoiced."""
        from app.models.work_order import TaskStatus

        already_certified = (
            select(CertificationItem.task_id)
            .join(Certification)
            .where(Certification.work_order_id == work_order_id)
            .where(Certification.status.in_(["issued", "invoiced"]))
        )
        result = await self.session.execute(
            select(Task)
            .where(Task.work_order_id == work_order_id)
            .where(Task.status == TaskStatus.COMPLETED)
            .where(Task.id.notin_(already_certified))
            .options(
                selectinload(Task.materials).selectinload(TaskMaterial.inventory_item),
                selectinload(Task.certification_items).selectinload(
                    CertificationItem.certification
                ),
            )
        )
        return list(result.scalars().all())


class TaskMaterialRepository(BaseRepository[TaskMaterial]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(TaskMaterial, session, tenant_id)


class CertificationRepository(BaseRepository[Certification]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(Certification, session, tenant_id)

    async def get_next_certification_number(
        self, work_order_number: str
    ) -> str:
        result = await self.session.execute(
            select(func.count(Certification.id))
            .join(WorkOrder)
            .where(WorkOrder.work_order_number == work_order_number)
        )
        count = result.scalar() or 0
        return f"CERT-{work_order_number}-{(count + 1):02d}"

    async def get_with_items(
        self, certification_id: uuid.UUID
    ) -> Certification | None:
        result = await self.session.execute(
            select(Certification)
            .options(
                selectinload(Certification.items).selectinload(
                    CertificationItem.task
                )
            )
            .where(Certification.id == certification_id)
        )
        return result.scalar_one_or_none()

    async def get_total_certified(self, work_order_id: uuid.UUID) -> Decimal:
        result = await self.session.execute(
            select(func.sum(CertificationItem.amount))
            .join(Certification)
            .where(Certification.work_order_id == work_order_id)
            .where(Certification.status.in_(["issued", "invoiced"]))
        )
        return result.scalar() or Decimal("0.0")


class CertificationItemRepository(BaseRepository[CertificationItem]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(CertificationItem, session, tenant_id)


class WorkOrderPurchaseOrderRepository(BaseRepository[WorkOrderPurchaseOrder]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(WorkOrderPurchaseOrder, session, tenant_id)


class DeliveryNoteRepository(BaseRepository[DeliveryNote]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(DeliveryNote, session, tenant_id)

    async def get_next_delivery_note_number(self, work_order_number: str) -> str:
        result = await self.session.execute(
            select(func.count(DeliveryNote.id))
            .join(WorkOrder)
            .where(WorkOrder.work_order_number == work_order_number)
        )
        count = result.scalar() or 0
        return f"ALBAR-{work_order_number}-{(count + 1):02d}"

    async def get_with_items(
        self, delivery_note_id: uuid.UUID
    ) -> DeliveryNote | None:
        result = await self.session.execute(
            select(DeliveryNote)
            .options(
                selectinload(DeliveryNote.items).selectinload(
                    DeliveryNoteItem.inventory_item
                )
            )
            .where(DeliveryNote.id == delivery_note_id)
        )
        return result.scalar_one_or_none()

    async def list_by_work_order(
        self, work_order_id: uuid.UUID
    ) -> list[DeliveryNote]:
        result = await self.session.execute(
            select(DeliveryNote)
            .options(
                selectinload(DeliveryNote.items).selectinload(
                    DeliveryNoteItem.inventory_item
                )
            )
            .where(DeliveryNote.work_order_id == work_order_id)
            .order_by(DeliveryNote.created_at.desc())
        )
        return list(result.scalars().all())


class DeliveryNoteItemRepository(BaseRepository[DeliveryNoteItem]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(DeliveryNoteItem, session, tenant_id)
