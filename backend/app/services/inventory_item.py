"""Service layer for InventoryItem business logic (used by suppliers module)."""

import logging
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_item import InventoryItem
from app.models.supplier_item import SupplierItem
from app.repositories.inventory_item import InventoryItemRepository
from app.repositories.supplier_item import SupplierItemRepository
from app.schemas.inventory_item import InventoryItemCreate, InventoryItemListResponse, InventoryItemResponse
from app.schemas.supplier_item import SupplierItemResponse

logger = logging.getLogger(__name__)


def _build_item_response(item: InventoryItem) -> InventoryItemResponse:
    """Build an InventoryItemResponse with computed fields from a loaded InventoryItem."""
    active_supplier_items = [si for si in item.supplier_items if si.is_active]
    preferred = next((si for si in active_supplier_items if si.is_preferred), None)

    def _si_response(si: SupplierItem) -> SupplierItemResponse:
        return SupplierItemResponse(
            id=si.id,
            supplier_id=si.supplier_id,
            supplier_name=si.supplier.name if si.supplier else "",
            inventory_item_id=si.inventory_item_id,
            supplier_ref=si.supplier_ref,
            unit_cost=si.unit_cost,
            last_purchase_cost=si.last_purchase_cost,
            last_purchase_date=si.last_purchase_date,
            lead_time_days=si.lead_time_days,
            is_preferred=si.is_preferred,
            is_active=si.is_active,
            created_at=si.created_at,
            updated_at=si.updated_at,
        )

    return InventoryItemResponse(
        id=item.id,
        name=item.name,
        description=item.description,
        unit=item.unit,
        unit_cost_avg=item.unit_cost_avg,
        unit_price=item.unit_price,
        stock_current=item.stock_current,
        stock_min=item.stock_min,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
        stock_reserved=Decimal("0"),
        stock_available=item.stock_current,
        low_stock_alert=item.stock_current <= item.stock_min,
        last_movement_at=item.stock_movements[0].created_at if item.stock_movements else None,
        supplier_items=[_si_response(si) for si in active_supplier_items],
        preferred_supplier=_si_response(preferred) if preferred else None,
    )


class InventoryItemService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.repo = InventoryItemRepository(session, tenant_id)
        self._supplier_item_repo = SupplierItemRepository(session, tenant_id)
        self._tenant_id = tenant_id
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
            items=[_build_item_response(i) for i in items],
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
            unit_price=data.unit_price,
            unit_cost_avg=Decimal("0"),
            stock_current=data.stock_current,
            stock_min=data.stock_min,
            is_active=True,
            tenant_id=self._tenant_id,
        )
        created = await self.repo.create(item)

        # Link item to this supplier via the junction table
        si = SupplierItem(
            supplier_id=supplier_id,
            inventory_item_id=created.id,
            unit_cost=Decimal("0"),
            is_preferred=True,
            is_active=True,
        )
        self._session.add(si)
        await self._session.flush()

        await self._session.commit()
        logger.info(
            "inventory_item.created id=%s name=%r supplier_id=%s",
            created.id,
            created.name,
            supplier_id,
        )
        result = await self.repo.get_with_supplier_items(created.id)
        return _build_item_response(result)
