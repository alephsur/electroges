"""Service layer for InventoryItem business logic."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_item import InventoryItem
from app.repositories.inventory_item import InventoryItemRepository


from app.schemas.inventory_item import InventoryItemCreate, InventoryItemListResponse, InventoryItemResponse

logger = logging.getLogger(__name__)


class InventoryItemService:
    def __init__(self, session: AsyncSession):
        self.repo = InventoryItemRepository(session)
        self._session = session

    async def list_for_supplier(
        self,
        supplier_id: uuid.UUID,
        *,
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 100,
    ) -> InventoryItemListResponse:
        items, total = await self.repo.get_by_supplier(
            supplier_id, is_active=is_active, skip=skip, limit=limit
        )
        logger.debug(
            "list_for_supplier supplier_id=%s total=%d is_active=%s",
            supplier_id,
            total,
            is_active,
        )
        return InventoryItemListResponse(
            items=[InventoryItemResponse.model_validate(i) for i in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def create_for_supplier(
        self, supplier_id: uuid.UUID, data: InventoryItemCreate
    ) -> InventoryItemResponse:
        item = InventoryItem(
            name=data.name,
            description=data.description,
            unit=data.unit,
            unit_cost=data.unit_cost,
            unit_price=data.unit_price,
            stock_current=data.stock_current,
            stock_min=data.stock_min,
            supplier_id=supplier_id,
            is_active=True,
        )
        created = await self.repo.create(item)
        await self._session.commit()
        logger.info(
            "inventory_item.created id=%s name=%r supplier_id=%s",
            created.id,
            created.name,
            supplier_id,
        )
        return InventoryItemResponse.model_validate(created)
