"""Service layer for PurchaseOrder business logic."""

import logging
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_item import InventoryItem
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.stock_movement import StockMovement
from app.repositories.inventory_item import InventoryItemRepository
from app.repositories.purchase_order import PurchaseOrderRepository
from app.repositories.stock_movement import StockMovementRepository
from app.repositories.supplier_item import SupplierItemRepository
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderListResponse,
    PurchaseOrderResponse,
    PurchaseOrderSummary,
    PurchaseOrderUpdate,
)

logger = logging.getLogger(__name__)


class PurchaseOrderService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self._repo = PurchaseOrderRepository(session, tenant_id)
        self._item_repo = InventoryItemRepository(session, tenant_id)
        self._movement_repo = StockMovementRepository(session, tenant_id)
        self._supplier_item_repo = SupplierItemRepository(session, tenant_id)
        self._tenant_id = tenant_id
        self._session = session

    async def list_by_supplier(
        self,
        supplier_id: uuid.UUID,
        *,
        status_filter: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> PurchaseOrderListResponse:
        rows, total = await self._repo.get_by_supplier(
            supplier_id, status=status_filter, skip=skip, limit=limit
        )
        logger.debug(
            "list_by_supplier supplier_id=%s total=%d status=%s",
            supplier_id,
            total,
            status_filter,
        )
        items = []
        for order, order_total in rows:
            summary = PurchaseOrderSummary.model_validate(order)
            summary.total = order_total
            items.append(summary)
        return PurchaseOrderListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_order(self, order_id: uuid.UUID) -> PurchaseOrderResponse:
        order = await self._repo.get_with_lines(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )
        return PurchaseOrderResponse.model_validate(order)

    async def create_order(self, data: PurchaseOrderCreate) -> PurchaseOrderResponse:
        order_number = await self._repo.get_next_order_number()
        logger.info(
            "purchase_order.creating supplier_id=%s order_number=%s lines=%d",
            data.supplier_id,
            order_number,
            len(data.lines),
        )

        order = PurchaseOrder(
            supplier_id=data.supplier_id,
            order_number=order_number,
            status="pending",
            order_date=data.order_date,
            expected_date=data.expected_date,
            notes=data.notes,
            tenant_id=self._tenant_id,
        )
        await self._repo.create(order)

        for line_data in data.lines:
            subtotal = (line_data.quantity * line_data.unit_cost).quantize(
                Decimal("0.0001")
            )
            line = PurchaseOrderLine(
                purchase_order_id=order.id,
                inventory_item_id=line_data.inventory_item_id,
                description=line_data.description,
                quantity=line_data.quantity,
                unit_cost=line_data.unit_cost,
                subtotal=subtotal,
            )
            self._session.add(line)

        await self._session.flush()
        await self._session.commit()
        logger.info("purchase_order.created id=%s order_number=%s", order.id, order_number)

        result = await self._repo.get_with_lines(order.id)
        return PurchaseOrderResponse.model_validate(result)

    async def update_order(
        self, order_id: uuid.UUID, data: PurchaseOrderUpdate
    ) -> PurchaseOrderResponse:
        order = await self._repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )
        if order.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solo se pueden modificar pedidos en estado 'pending'",
            )
        update_data = data.model_dump(exclude_unset=True)
        await self._repo.update(order, update_data)
        await self._session.commit()
        logger.info("purchase_order.updated id=%s", order_id)

        result = await self._repo.get_with_lines(order_id)
        return PurchaseOrderResponse.model_validate(result)

    async def receive_order(self, order_id: uuid.UUID) -> PurchaseOrderResponse:
        """Mark order as received, create StockMovements and update PMP for each line."""
        from datetime import date as date_type

        order = await self._repo.get_with_lines(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )
        if order.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solo se pueden recibir pedidos en estado 'pending'",
            )

        logger.info("purchase_order.receiving id=%s lines=%d", order_id, len(order.lines))

        today = date_type.today()

        for line in order.lines:
            if line.inventory_item_id is None:
                continue

            item = await self._item_repo.get_by_id(line.inventory_item_id)
            if item is None:
                logger.warning(
                    "receive_order: inventory_item_id=%s not found, skipping",
                    line.inventory_item_id,
                )
                continue

            # 1. Persist the StockMovement first (must be flushed before PMP calc)
            movement = StockMovement(
                inventory_item_id=line.inventory_item_id,
                movement_type="entry",
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                reference_type="purchase_order",
                reference_id=order.id,
                tenant_id=self._tenant_id,
            )
            await self._movement_repo.create(movement)

            # 2. Calculate PMP now that the movement is in the session
            new_pmp = await self._movement_repo.calculate_pmp(line.inventory_item_id)

            # 3. Atomic stock + PMP update
            await self._item_repo.update_stock_and_pmp(
                line.inventory_item_id, line.quantity, new_pmp
            )
            logger.debug(
                "stock_entry item_id=%s qty=%.3f new_pmp=%.4f",
                item.id,
                line.quantity,
                new_pmp,
            )

            # 4. Update SupplierItem pricing (prefer explicit link, fall back to supplier lookup)
            supplier_item = None
            if line.supplier_item_id is not None:
                supplier_item = await self._supplier_item_repo.get_by_id(
                    line.supplier_item_id
                )
            if supplier_item is None:
                supplier_item = await self._supplier_item_repo.get_by_supplier_and_item(
                    order.supplier_id, line.inventory_item_id
                )
            if supplier_item is not None:
                await self._supplier_item_repo.update(
                    supplier_item,
                    {
                        "last_purchase_cost": line.unit_cost,
                        "last_purchase_date": today,
                        "unit_cost": line.unit_cost,
                    },
                )

        await self._repo.update(
            order,
            {"status": "received", "received_date": today},
        )
        await self._session.commit()
        logger.info("purchase_order.received id=%s", order_id)

        result = await self._repo.get_with_lines(order_id)
        return PurchaseOrderResponse.model_validate(result)

    async def cancel_order(self, order_id: uuid.UUID) -> PurchaseOrderResponse:
        order = await self._repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )
        if order.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solo se pueden cancelar pedidos en estado 'pending'",
            )
        await self._repo.update(order, {"status": "cancelled"})
        await self._session.commit()
        logger.info("purchase_order.cancelled id=%s", order_id)

        result = await self._repo.get_with_lines(order_id)
        return PurchaseOrderResponse.model_validate(result)
