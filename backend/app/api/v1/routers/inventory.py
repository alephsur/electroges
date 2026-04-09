import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentTenantId, CurrentUser, DbSession
from app.schemas.inventory_item import (
    InventoryItemCreateWithSupplier,
    InventoryItemListResponse,
    InventoryItemResponse,
    InventoryItemUpdate,
)
from app.schemas.stock_movement import ManualAdjustmentRequest, StockMovementResponse
from app.schemas.supplier_item import SupplierItemCreate, SupplierItemResponse, SupplierItemUpdate
from app.services.inventory import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventario"])


# ------------------------------------------------------------------ items

@router.get("", response_model=InventoryItemListResponse)
async def list_inventory_items(
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
    q: str | None = Query(default=None, description="Search by name or description"),
    supplier_id: uuid.UUID | None = Query(default=None),
    low_stock_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
):
    return await InventoryService(db, tenant_id).list_items(
        query=q,
        supplier_id=supplier_id,
        low_stock_only=low_stock_only,
        skip=skip,
        limit=limit,
    )


@router.get("/alerts", response_model=list[InventoryItemResponse])
async def get_low_stock_alerts(db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId):
    """Return items at or below their minimum stock threshold."""
    return await InventoryService(db, tenant_id).get_low_stock_alerts()


@router.get("/{item_id}", response_model=InventoryItemResponse)
async def get_inventory_item(item_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId):
    return await InventoryService(db, tenant_id).get_item(item_id)


@router.post("", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    data: InventoryItemCreateWithSupplier, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    return await InventoryService(db, tenant_id).create_item(data)


@router.patch("/{item_id}", response_model=InventoryItemResponse)
async def update_inventory_item(
    item_id: uuid.UUID, data: InventoryItemUpdate, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    return await InventoryService(db, tenant_id).update_item(item_id, data)


@router.delete("/{item_id}", response_model=InventoryItemResponse)
async def deactivate_inventory_item(item_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId):
    return await InventoryService(db, tenant_id).deactivate_item(item_id)


# ------------------------------------------------------------------ suppliers per item

@router.get("/{item_id}/suppliers", response_model=list[SupplierItemResponse])
async def list_item_suppliers(item_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId):
    return await InventoryService(db, tenant_id).get_item_suppliers(item_id)


@router.post(
    "/{item_id}/suppliers",
    response_model=SupplierItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_supplier_to_item(
    item_id: uuid.UUID, data: SupplierItemCreate, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    # Ensure inventory_item_id matches the path parameter
    patched = data.model_copy(update={"inventory_item_id": item_id})
    return await InventoryService(db, tenant_id).add_supplier(item_id, patched)


@router.patch("/{item_id}/suppliers/{supplier_item_id}", response_model=SupplierItemResponse)
async def update_supplier_price(
    item_id: uuid.UUID,
    supplier_item_id: uuid.UUID,
    data: SupplierItemUpdate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    return await InventoryService(db, tenant_id).update_supplier_price(item_id, supplier_item_id, data)


@router.delete("/{item_id}/suppliers/{supplier_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_supplier_from_item(
    item_id: uuid.UUID,
    supplier_item_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    await InventoryService(db, tenant_id).remove_supplier(item_id, supplier_item_id)


@router.post(
    "/{item_id}/suppliers/{supplier_item_id}/set-preferred",
    response_model=SupplierItemResponse,
)
async def set_preferred_supplier(
    item_id: uuid.UUID,
    supplier_item_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    return await InventoryService(db, tenant_id).set_preferred_supplier(item_id, supplier_item_id)


# ------------------------------------------------------------------ stock

@router.post("/{item_id}/adjust", response_model=InventoryItemResponse)
async def manual_stock_adjustment(
    item_id: uuid.UUID, data: ManualAdjustmentRequest, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    return await InventoryService(db, tenant_id).manual_adjustment(item_id, data)


@router.get("/{item_id}/movements", response_model=list[StockMovementResponse])
async def list_item_movements(
    item_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    return await InventoryService(db, tenant_id).get_movements(item_id, skip, limit)
