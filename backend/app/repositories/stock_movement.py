"""Repository for StockMovement persistence operations."""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_movement import StockMovement
from app.repositories.base import BaseRepository


class StockMovementRepository(BaseRepository[StockMovement]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(StockMovement, session, tenant_id)

    async def get_by_item(
        self,
        inventory_item_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[StockMovement]:
        """Return paginated movement history for an item, most recent first."""
        result = await self.session.execute(
            select(StockMovement)
            .where(StockMovement.inventory_item_id == inventory_item_id)
            .order_by(StockMovement.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_reference(
        self, reference_type: str, reference_id: uuid.UUID
    ) -> list[StockMovement]:
        """Return all movements related to a purchase order or work order."""
        result = await self.session.execute(
            select(StockMovement)
            .where(StockMovement.reference_type == reference_type)
            .where(StockMovement.reference_id == reference_id)
            .order_by(StockMovement.created_at)
        )
        return list(result.scalars().all())

    async def calculate_pmp(self, inventory_item_id: uuid.UUID) -> Decimal:
        """Calculate the weighted average cost (PMP) based on all entry movements.

        Must be called AFTER the new StockMovement has been flushed to the session,
        so it is included in the calculation.
        """
        result = await self.session.execute(
            select(
                func.sum(StockMovement.quantity * StockMovement.unit_cost),
                func.sum(StockMovement.quantity),
            )
            .where(StockMovement.inventory_item_id == inventory_item_id)
            .where(StockMovement.movement_type == "entry")
        )
        row = result.one()
        total_value, total_qty = row[0], row[1]
        if not total_qty or total_qty == 0:
            return Decimal("0.0")
        return (total_value / total_qty).quantize(Decimal("0.0001"))
