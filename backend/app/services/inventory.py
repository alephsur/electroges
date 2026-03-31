"""Service layer for Inventory module business logic."""

import logging
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_item import InventoryItem
from app.models.stock_movement import StockMovement
from app.models.supplier_item import SupplierItem
from app.repositories.inventory_item import InventoryItemRepository
from app.repositories.stock_movement import StockMovementRepository
from app.repositories.supplier_item import SupplierItemRepository
from app.schemas.inventory_item import (
    InventoryItemCreateWithSupplier,
    InventoryItemListResponse,
    InventoryItemResponse,
    InventoryItemUpdate,
)
from app.schemas.stock_movement import ManualAdjustmentRequest, StockMovementResponse
from app.schemas.supplier_item import (
    SupplierItemCreate,
    SupplierItemResponse,
    SupplierItemUpdate,
)

logger = logging.getLogger(__name__)


class InventoryService:
    def __init__(self, session: AsyncSession):
        self._item_repo = InventoryItemRepository(session)
        self._movement_repo = StockMovementRepository(session)
        self._supplier_item_repo = SupplierItemRepository(session)
        self._session = session

    # ------------------------------------------------------------------ items

    async def list_items(
        self,
        query: str | None,
        supplier_id: uuid.UUID | None,
        low_stock_only: bool,
        skip: int,
        limit: int,
    ) -> InventoryItemListResponse:
        items, total = await self._item_repo.search_inventory(
            query,
            supplier_id=supplier_id,
            low_stock_only=low_stock_only,
            skip=skip,
            limit=limit,
        )
        return InventoryItemListResponse(
            items=[self._enrich_item(i) for i in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_item(self, item_id: uuid.UUID) -> InventoryItemResponse:
        item = await self._item_repo.get_with_full_detail(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material no encontrado",
            )
        return self._enrich_item(item)

    async def create_item(
        self, data: InventoryItemCreateWithSupplier
    ) -> InventoryItemResponse:
        item = InventoryItem(
            name=data.name,
            description=data.description,
            unit=data.unit,
            unit_price=data.unit_price,
            unit_cost=data.unit_cost,
            unit_cost_avg=Decimal("0"),
            stock_current=Decimal("0"),
            stock_min=data.stock_min,
            supplier_id=data.supplier_id,
            is_active=data.is_active,
        )
        created = await self._item_repo.create(item)

        if data.supplier_id is not None and data.unit_cost > 0:
            supplier_item = SupplierItem(
                supplier_id=data.supplier_id,
                inventory_item_id=created.id,
                unit_cost=data.unit_cost,
                supplier_ref=data.supplier_ref,
                is_preferred=True,
                is_active=True,
            )
            self._session.add(supplier_item)
            await self._session.flush()

        await self._session.commit()
        logger.info("inventory_item.created id=%s name=%r", created.id, created.name)

        result = await self._item_repo.get_with_supplier_items(created.id)
        return self._enrich_item(result)

    async def update_item(
        self, item_id: uuid.UUID, data: InventoryItemUpdate
    ) -> InventoryItemResponse:
        item = await self._item_repo.get_with_supplier_items(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material no encontrado",
            )

        update_data = data.model_dump(exclude_unset=True)
        await self._item_repo.update(item, update_data)
        await self._session.commit()
        logger.info("inventory_item.updated id=%s", item_id)

        result = await self._item_repo.get_with_supplier_items(item_id)
        return self._enrich_item(result)

    async def deactivate_item(self, item_id: uuid.UUID) -> InventoryItemResponse:
        item = await self._item_repo.get_by_id(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material no encontrado",
            )
        await self._item_repo.update(item, {"is_active": False})
        await self._session.commit()
        logger.info("inventory_item.deactivated id=%s", item_id)
        return InventoryItemResponse(
            id=item.id,
            name=item.name,
            description=item.description,
            unit=item.unit,
            unit_cost=item.unit_cost,
            unit_cost_avg=item.unit_cost_avg,
            unit_price=item.unit_price,
            stock_current=item.stock_current,
            stock_min=item.stock_min,
            supplier_id=item.supplier_id,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
            stock_reserved=item.stock_reserved,
            stock_available=item.stock_current - item.stock_reserved,
            low_stock_alert=(item.stock_current - item.stock_reserved) <= item.stock_min,
        )

    # ------------------------------------------------------------------ suppliers

    async def get_item_suppliers(self, item_id: uuid.UUID) -> list[SupplierItemResponse]:
        self._require_item(await self._item_repo.get_by_id(item_id))
        supplier_items = await self._supplier_item_repo.get_by_item(item_id)
        return [self._build_supplier_item_response(si) for si in supplier_items]

    async def add_supplier(
        self, item_id: uuid.UUID, data: SupplierItemCreate
    ) -> SupplierItemResponse:
        self._require_item(await self._item_repo.get_by_id(item_id))

        existing = await self._supplier_item_repo.get_by_supplier_and_item(
            data.supplier_id, item_id
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este proveedor ya está vinculado a este material",
            )

        # If this supplier will be preferred, clear existing preferred flags first
        if data.is_preferred:
            from sqlalchemy import update as sa_update

            await self._session.execute(
                sa_update(SupplierItem)
                .where(SupplierItem.inventory_item_id == item_id)
                .values(is_preferred=False)
            )

        supplier_item = SupplierItem(
            supplier_id=data.supplier_id,
            inventory_item_id=item_id,
            unit_cost=data.unit_cost,
            supplier_ref=data.supplier_ref,
            lead_time_days=data.lead_time_days,
            is_preferred=data.is_preferred,
            is_active=True,
        )
        created = await self._supplier_item_repo.create(supplier_item)
        await self._session.commit()
        logger.info(
            "supplier_item.added item_id=%s supplier_id=%s", item_id, data.supplier_id
        )

        result = await self._supplier_item_repo.get_by_id_with_supplier(created.id)
        return self._build_supplier_item_response(result)

    async def update_supplier_price(
        self, item_id: uuid.UUID, supplier_item_id: uuid.UUID, data: SupplierItemUpdate
    ) -> SupplierItemResponse:
        si = await self._supplier_item_repo.get_by_id_with_supplier(supplier_item_id)
        if not si or si.inventory_item_id != item_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vínculo proveedor-material no encontrado",
            )

        update_data = data.model_dump(exclude_unset=True)
        setting_preferred = update_data.pop("is_preferred", None)

        if update_data:
            await self._supplier_item_repo.update(si, update_data)

        if setting_preferred is True:
            await self._supplier_item_repo.set_preferred(supplier_item_id)
            # Sync unit_cost on the inventory item to the preferred supplier's price
            item = await self._item_repo.get_by_id(item_id)
            if item:
                # Use the updated unit_cost if it was part of this update, else current
                new_cost = data.unit_cost if data.unit_cost is not None else si.unit_cost
                await self._item_repo.update(item, {"unit_cost": new_cost})

        await self._session.commit()
        logger.info("supplier_item.updated id=%s", supplier_item_id)

        result = await self._supplier_item_repo.get_by_id_with_supplier(supplier_item_id)
        return self._build_supplier_item_response(result)

    async def remove_supplier(self, item_id: uuid.UUID, supplier_item_id: uuid.UUID) -> None:
        si = await self._supplier_item_repo.get_by_id_with_supplier(supplier_item_id)
        if not si or si.inventory_item_id != item_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vínculo proveedor-material no encontrado",
            )

        active_suppliers = await self._supplier_item_repo.get_by_item(item_id)
        if len(active_suppliers) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar el único proveedor del material. "
                "Añade otro proveedor antes de eliminar este.",
            )
        if si.is_preferred:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Designa otro proveedor como preferido antes de eliminar este.",
            )

        await self._supplier_item_repo.update(si, {"is_active": False})
        await self._session.commit()
        logger.info("supplier_item.removed id=%s", supplier_item_id)

    async def set_preferred_supplier(
        self, item_id: uuid.UUID, supplier_item_id: uuid.UUID
    ) -> SupplierItemResponse:
        si = await self._supplier_item_repo.get_by_id_with_supplier(supplier_item_id)
        if not si or si.inventory_item_id != item_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vínculo proveedor-material no encontrado",
            )

        await self._supplier_item_repo.set_preferred(supplier_item_id)

        # Sync unit_cost on inventory item to the preferred supplier's price
        item = await self._item_repo.get_by_id(item_id)
        if item:
            await self._item_repo.update(item, {"unit_cost": si.unit_cost})

        await self._session.commit()
        logger.info(
            "supplier_item.set_preferred id=%s item_id=%s", supplier_item_id, item_id
        )

        result = await self._supplier_item_repo.get_by_id_with_supplier(supplier_item_id)
        return self._build_supplier_item_response(result)

    # ------------------------------------------------------------------ stock

    async def manual_adjustment(
        self, item_id: uuid.UUID, data: ManualAdjustmentRequest
    ) -> InventoryItemResponse:
        item = await self._item_repo.get_by_id(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material no encontrado",
            )

        if data.quantity < 0 and abs(data.quantity) > item.stock_current:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"La cantidad a descontar ({abs(data.quantity)}) "
                    f"supera el stock disponible ({item.stock_current})"
                ),
            )

        movement_type = "entry" if data.quantity > 0 else "exit"
        movement = StockMovement(
            inventory_item_id=item_id,
            movement_type=movement_type,
            quantity=abs(data.quantity),
            unit_cost=data.unit_cost,
            reference_type="manual_adjustment",
            notes=data.notes,
        )
        await self._movement_repo.create(movement)

        # PMP must be recalculated AFTER the movement is flushed
        new_pmp = item.unit_cost_avg
        if movement_type == "entry":
            new_pmp = await self._movement_repo.calculate_pmp(item_id)

        await self._item_repo.update_stock_and_pmp(item_id, data.quantity, new_pmp)
        await self._session.commit()
        logger.info(
            "stock.manual_adjustment item_id=%s type=%s qty=%s",
            item_id,
            movement_type,
            data.quantity,
        )

        result = await self._item_repo.get_with_full_detail(item_id)
        return self._enrich_item(result)

    async def get_movements(
        self, item_id: uuid.UUID, skip: int, limit: int
    ) -> list[StockMovementResponse]:
        self._require_item(await self._item_repo.get_by_id(item_id))
        movements = await self._movement_repo.get_by_item(item_id, skip=skip, limit=limit)
        return [self._build_movement_response(m) for m in movements]

    async def get_low_stock_alerts(self) -> list[InventoryItemResponse]:
        items = await self._item_repo.get_low_stock_items()
        return [self._enrich_item(i) for i in items]

    # ------------------------------------------------------------------ helpers

    def _require_item(self, item: InventoryItem | None) -> InventoryItem:
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material no encontrado",
            )
        return item

    def _enrich_item(self, item: InventoryItem) -> InventoryItemResponse:
        """Build InventoryItemResponse with computed fields.

        Uses direct construction (not model_validate) to avoid Pydantic trying to
        auto-validate ORM relationships that contain computed fields (e.g. supplier_name).
        """
        # Use the atomically-maintained stock_reserved column (updated by WorkOrderService)
        stock_reserved = item.stock_reserved
        stock_available = item.stock_current - stock_reserved
        low_stock_alert = stock_available <= item.stock_min

        active_supplier_items = [si for si in item.supplier_items if si.is_active]
        preferred = next((si for si in active_supplier_items if si.is_preferred), None)

        last_movement_at = (
            item.stock_movements[0].created_at if item.stock_movements else None
        )

        return InventoryItemResponse(
            id=item.id,
            name=item.name,
            description=item.description,
            unit=item.unit,
            unit_cost=item.unit_cost,
            unit_cost_avg=item.unit_cost_avg,
            unit_price=item.unit_price,
            stock_current=item.stock_current,
            stock_min=item.stock_min,
            supplier_id=item.supplier_id,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
            stock_reserved=stock_reserved,
            stock_available=stock_available,
            low_stock_alert=low_stock_alert,
            last_movement_at=last_movement_at,
            supplier_items=[
                self._build_supplier_item_response(si) for si in active_supplier_items
            ],
            preferred_supplier=(
                self._build_supplier_item_response(preferred) if preferred else None
            ),
        )

    @staticmethod
    def _build_supplier_item_response(si: SupplierItem) -> SupplierItemResponse:
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

    @staticmethod
    def _build_movement_response(m: StockMovement) -> StockMovementResponse:
        # inventory_item_name is populated by the detail endpoint via get_with_full_detail
        # For the /movements endpoint we skip the join and use an empty string placeholder
        try:
            item_name = m.inventory_item.name if m.inventory_item else ""
        except Exception:
            item_name = ""
        return StockMovementResponse(
            id=m.id,
            inventory_item_id=m.inventory_item_id,
            inventory_item_name=item_name,
            movement_type=m.movement_type,
            quantity=m.quantity,
            unit_cost=m.unit_cost,
            reference_type=m.reference_type,
            reference_id=m.reference_id,
            notes=m.notes,
            created_at=m.created_at,
        )
