"""Repository for InventoryItem persistence operations."""

import uuid
from decimal import Decimal

from sqlalchemy import exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory_item import InventoryItem
from app.models.stock_movement import StockMovement
from app.models.supplier_item import SupplierItem
from app.repositories.base import BaseRepository


class InventoryItemRepository(BaseRepository[InventoryItem]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(InventoryItem, session, tenant_id)

    async def get_by_supplier(
        self,
        supplier_id: uuid.UUID,
        *,
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[InventoryItem], int]:
        """Items linked to a supplier via the SupplierItem junction table (active entries only)."""
        linked_via_junction = exists().where(
            (SupplierItem.inventory_item_id == InventoryItem.id)
            & (SupplierItem.supplier_id == supplier_id)
            & (SupplierItem.is_active.is_(True))
        )
        query = select(InventoryItem).where(linked_via_junction)
        if self.tenant_id is not None:
            query = query.where(InventoryItem.tenant_id == self.tenant_id)
        if is_active is not None:
            query = query.where(InventoryItem.is_active == is_active)

        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            query
            .options(
                selectinload(InventoryItem.supplier_items).selectinload(SupplierItem.supplier),
                selectinload(InventoryItem.stock_movements),
            )
            .order_by(InventoryItem.name)
            .offset(skip)
            .limit(limit)
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
        """Legacy search used internally by suppliers module."""
        query = select(InventoryItem).where(InventoryItem.name.ilike(f"%{q}%"))
        if self.tenant_id is not None:
            query = query.where(InventoryItem.tenant_id == self.tenant_id)
        if supplier_id is not None:
            linked_via_junction = exists().where(
                (SupplierItem.inventory_item_id == InventoryItem.id)
                & (SupplierItem.supplier_id == supplier_id)
                & (SupplierItem.is_active.is_(True))
            )
            query = query.where(linked_via_junction)
        if is_active is not None:
            query = query.where(InventoryItem.is_active == is_active)

        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            query
            .options(
                selectinload(InventoryItem.supplier_items).selectinload(SupplierItem.supplier),
                selectinload(InventoryItem.stock_movements),
            )
            .order_by(InventoryItem.name)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def search_inventory(
        self,
        query: str | None,
        *,
        supplier_id: uuid.UUID | None,
        low_stock_only: bool,
        skip: int,
        limit: int,
    ) -> tuple[list[InventoryItem], int]:
        """Full inventory search with filters. Filters by supplier via supplier_items join."""
        base_query = (
            select(InventoryItem)
            .where(InventoryItem.is_active == True)  # noqa: E712
        )
        if self.tenant_id is not None:
            base_query = base_query.where(InventoryItem.tenant_id == self.tenant_id)

        if query:
            base_query = base_query.where(
                InventoryItem.name.ilike(f"%{query}%")
                | InventoryItem.description.ilike(f"%{query}%")
            )

        if supplier_id is not None:
            base_query = base_query.join(
                SupplierItem,
                (SupplierItem.inventory_item_id == InventoryItem.id)
                & (SupplierItem.supplier_id == supplier_id)
                & (SupplierItem.is_active == True),  # noqa: E712
            )

        if low_stock_only:
            base_query = base_query.where(
                InventoryItem.stock_current <= InventoryItem.stock_min
            )

        count_result = await self.session.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            base_query
            .options(
                selectinload(InventoryItem.supplier_items).selectinload(SupplierItem.supplier),
                selectinload(InventoryItem.stock_movements),
            )
            .order_by(InventoryItem.name)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_with_full_detail(self, item_id: uuid.UUID) -> InventoryItem | None:
        """Eager-load supplier_items (with supplier) and last 20 stock_movements."""
        # Load supplier_items with their supplier in one query
        result = await self.session.execute(
            select(InventoryItem)
            .where(InventoryItem.id == item_id)
            .options(
                selectinload(InventoryItem.supplier_items).selectinload(SupplierItem.supplier),
                selectinload(InventoryItem.stock_movements),
            )
        )
        item = result.scalar_one_or_none()
        if item is not None:
            # Trim movements to 20 most recent (already sorted desc by relationship order_by)
            item.stock_movements = item.stock_movements[:20]
        return item

    async def get_low_stock_items(self) -> list[InventoryItem]:
        """Items where available stock is at or below the minimum threshold."""
        stmt = (
            select(InventoryItem)
            .where(InventoryItem.is_active == True)  # noqa: E712
            .where(InventoryItem.stock_current <= InventoryItem.stock_min)
            .options(
                selectinload(InventoryItem.supplier_items).selectinload(SupplierItem.supplier),
                selectinload(InventoryItem.stock_movements),
            )
            .order_by(InventoryItem.name)
        )
        if self.tenant_id is not None:
            stmt = stmt.where(InventoryItem.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_stock_and_pmp(
        self,
        item_id: uuid.UUID,
        stock_delta: Decimal,
        new_pmp: Decimal,
    ) -> None:
        """Atomic stock + PMP update. Never use read-modify-write for stock changes."""
        await self.session.execute(
            update(InventoryItem)
            .where(InventoryItem.id == item_id)
            .values(
                stock_current=InventoryItem.stock_current + stock_delta,
                unit_cost_avg=new_pmp,
            )
        )

    async def get_with_supplier_items(self, item_id: uuid.UUID) -> InventoryItem | None:
        """Load item with supplier_items and stock_movements."""
        result = await self.session.execute(
            select(InventoryItem)
            .where(InventoryItem.id == item_id)
            .options(
                selectinload(InventoryItem.supplier_items).selectinload(SupplierItem.supplier),
                selectinload(InventoryItem.stock_movements),
            )
        )
        return result.scalar_one_or_none()
