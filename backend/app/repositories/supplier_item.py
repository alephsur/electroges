"""Repository for SupplierItem persistence operations."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.supplier_item import SupplierItem
from app.repositories.base import BaseRepository


class SupplierItemRepository(BaseRepository[SupplierItem]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(SupplierItem, session, tenant_id)

    async def get_by_item(self, inventory_item_id: uuid.UUID) -> list[SupplierItem]:
        """Return all active suppliers for an item, preferred first."""
        result = await self.session.execute(
            select(SupplierItem)
            .where(SupplierItem.inventory_item_id == inventory_item_id)
            .where(SupplierItem.is_active == True)  # noqa: E712
            .order_by(SupplierItem.is_preferred.desc(), SupplierItem.created_at)
            .options(selectinload(SupplierItem.supplier))
        )
        return list(result.scalars().all())

    async def get_by_supplier(self, supplier_id: uuid.UUID) -> list[SupplierItem]:
        """Return all active SupplierItems for a supplier (used by Materiales tab)."""
        result = await self.session.execute(
            select(SupplierItem)
            .where(SupplierItem.supplier_id == supplier_id)
            .where(SupplierItem.is_active == True)  # noqa: E712
            .options(selectinload(SupplierItem.inventory_item))
        )
        return list(result.scalars().all())

    async def get_preferred(self, inventory_item_id: uuid.UUID) -> SupplierItem | None:
        """Return the preferred supplier for an item, or None."""
        result = await self.session.execute(
            select(SupplierItem)
            .where(SupplierItem.inventory_item_id == inventory_item_id)
            .where(SupplierItem.is_preferred == True)  # noqa: E712
            .where(SupplierItem.is_active == True)  # noqa: E712
            .options(selectinload(SupplierItem.supplier))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def set_preferred(self, supplier_item_id: uuid.UUID) -> None:
        """Atomically set one SupplierItem as preferred and clear all others for the same item.

        Two-step UPDATE to avoid race conditions:
        1. Fetch the target item's inventory_item_id.
        2. Clear is_preferred for all siblings, then set it on the target.
        """
        result = await self.session.execute(
            select(SupplierItem.inventory_item_id).where(SupplierItem.id == supplier_item_id)
        )
        inventory_item_id = result.scalar_one_or_none()
        if inventory_item_id is None:
            return

        # Clear all current preferred flags for this item
        await self.session.execute(
            update(SupplierItem)
            .where(SupplierItem.inventory_item_id == inventory_item_id)
            .where(SupplierItem.id != supplier_item_id)
            .values(is_preferred=False)
        )
        # Activate the chosen one
        await self.session.execute(
            update(SupplierItem)
            .where(SupplierItem.id == supplier_item_id)
            .values(is_preferred=True)
        )

    async def get_by_supplier_and_item(
        self, supplier_id: uuid.UUID, inventory_item_id: uuid.UUID
    ) -> SupplierItem | None:
        """Return an existing link between supplier and item (to avoid duplicates)."""
        result = await self.session.execute(
            select(SupplierItem)
            .where(SupplierItem.supplier_id == supplier_id)
            .where(SupplierItem.inventory_item_id == inventory_item_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_supplier(self, supplier_item_id: uuid.UUID) -> SupplierItem | None:
        """Return a SupplierItem with its supplier eagerly loaded."""
        result = await self.session.execute(
            select(SupplierItem)
            .where(SupplierItem.id == supplier_item_id)
            .options(selectinload(SupplierItem.supplier))
        )
        return result.scalar_one_or_none()
