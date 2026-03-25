"""Repository for PurchaseOrder and PurchaseOrderLine persistence operations."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.repositories.base import BaseRepository


class PurchaseOrderRepository(BaseRepository[PurchaseOrder]):
    def __init__(self, session: AsyncSession):
        super().__init__(PurchaseOrder, session)

    async def get_by_supplier(
        self,
        supplier_id: uuid.UUID,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[tuple[PurchaseOrder, Decimal]], int]:
        """Return orders with their precomputed totals (correlated subquery)."""
        # Correlated subquery: sum of subtotals for each order
        total_sq = (
            select(func.coalesce(func.sum(PurchaseOrderLine.subtotal), 0))
            .where(PurchaseOrderLine.purchase_order_id == PurchaseOrder.id)
            .correlate(PurchaseOrder)
            .scalar_subquery()
        )

        base_filter = [PurchaseOrder.supplier_id == supplier_id]
        if status is not None:
            base_filter.append(PurchaseOrder.status == status)

        count_result = await self.session.execute(
            select(func.count(PurchaseOrder.id)).where(*base_filter)
        )
        total_count = count_result.scalar_one()

        result = await self.session.execute(
            select(PurchaseOrder, total_sq.label("order_total"))
            .where(*base_filter)
            .order_by(PurchaseOrder.order_date.desc())
            .offset(skip)
            .limit(limit)
        )
        rows = result.all()
        return [(order, Decimal(str(order_total))) for order, order_total in rows], total_count

    async def get_with_lines(self, order_id: uuid.UUID) -> PurchaseOrder | None:
        result = await self.session.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == order_id)
            .options(
                selectinload(PurchaseOrder.lines).selectinload(
                    PurchaseOrderLine.inventory_item
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_next_order_number(self) -> str:
        """Generate the next sequential order number in the format PED-YYYY-NNNN."""
        current_year = date.today().year
        result = await self.session.execute(
            select(func.count(PurchaseOrder.id)).where(
                extract("year", PurchaseOrder.order_date) == current_year
            )
        )
        count = result.scalar_one()
        return f"PED-{current_year}-{count + 1:04d}"
