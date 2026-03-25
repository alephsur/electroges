"""Repository for InventoryItem persistence operations."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_item import InventoryItem
from app.repositories.base import BaseRepository


class InventoryItemRepository(BaseRepository[InventoryItem]):
    def __init__(self, session: AsyncSession):
        super().__init__(InventoryItem, session)

    async def get_by_supplier(
        self,
        supplier_id: uuid.UUID,
        *,
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[InventoryItem], int]:
        query = select(InventoryItem).where(InventoryItem.supplier_id == supplier_id)
        if is_active is not None:
            query = query.where(InventoryItem.is_active == is_active)

        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            query.order_by(InventoryItem.name).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    async def search(
        self,
        q: str,
        *,
        supplier_id: uuid.UUID | None = None,
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[InventoryItem], int]:
        query = select(InventoryItem).where(InventoryItem.name.ilike(f"%{q}%"))
        if supplier_id is not None:
            query = query.where(InventoryItem.supplier_id == supplier_id)
        if is_active is not None:
            query = query.where(InventoryItem.is_active == is_active)

        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            query.order_by(InventoryItem.name).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total
