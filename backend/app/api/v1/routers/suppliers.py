import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentTenantId, CurrentUser, DbSession
from app.schemas.inventory_item import InventoryItemCreate, InventoryItemListResponse, InventoryItemResponse
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderListResponse,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
)
from app.schemas.supplier import (
    SupplierCreate,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdate,
)
from app.services.inventory_item import InventoryItemService
from app.services.purchase_order import PurchaseOrderService
from app.services.supplier import SupplierService

router = APIRouter(prefix="/suppliers", tags=["Proveedores"])


# ------------------------------------------------------------------ suppliers

@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
    q: str | None = Query(default=None, description="Search by name or tax ID"),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
):
    """Return a paginated list of suppliers with optional filters."""
    return await SupplierService(db, tenant_id).list_suppliers(
        q=q, is_active=is_active, skip=skip, limit=limit
    )


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(supplier_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId):
    """Return a single supplier by ID."""
    return await SupplierService(db, tenant_id).get_supplier(supplier_id)


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(data: SupplierCreate, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId):
    """Create a new supplier."""
    return await SupplierService(db, tenant_id).create_supplier(data)


@router.patch("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: uuid.UUID, data: SupplierUpdate, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId
):
    """Partially update a supplier."""
    return await SupplierService(db, tenant_id).update_supplier(supplier_id, data)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_supplier(supplier_id: uuid.UUID, db: DbSession, _: CurrentUser, tenant_id: CurrentTenantId):
    """Soft-delete a supplier (sets is_active = False)."""
    await SupplierService(db, tenant_id).deactivate_supplier(supplier_id)


# ------------------------------------------------------------------ inventory items

@router.get(
    "/{supplier_id}/inventory-items",
    response_model=InventoryItemListResponse,
)
async def list_supplier_inventory_items(
    supplier_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
):
    """Return paginated inventory items linked to a supplier."""
    return await InventoryItemService(db, tenant_id).list_for_supplier(
        supplier_id, is_active=is_active, skip=skip, limit=limit
    )


@router.post(
    "/{supplier_id}/inventory-items",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_supplier_inventory_item(
    supplier_id: uuid.UUID,
    data: InventoryItemCreate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    """Create a new inventory item linked to this supplier."""
    return await InventoryItemService(db, tenant_id).create_for_supplier(supplier_id, data)


# ------------------------------------------------------------------ purchase orders

@router.get("/{supplier_id}/purchase-orders", response_model=PurchaseOrderListResponse)
async def list_supplier_purchase_orders(
    supplier_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Return paginated purchase orders for a supplier."""
    return await PurchaseOrderService(db, tenant_id).list_by_supplier(
        supplier_id, status_filter=status_filter, skip=skip, limit=limit
    )


@router.post(
    "/{supplier_id}/purchase-orders",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_purchase_order(
    supplier_id: uuid.UUID,
    data: PurchaseOrderCreate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    """Create a new purchase order for a supplier."""
    # Ensure the supplier_id in the URL takes precedence
    data = data.model_copy(update={"supplier_id": supplier_id})
    return await PurchaseOrderService(db, tenant_id).create_order(data)


@router.get(
    "/{supplier_id}/purchase-orders/{order_id}",
    response_model=PurchaseOrderResponse,
)
async def get_purchase_order(
    supplier_id: uuid.UUID,  # noqa: ARG001 — kept for route consistency
    order_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    """Return a purchase order with all its lines."""
    return await PurchaseOrderService(db, tenant_id).get_order(order_id)


@router.patch(
    "/{supplier_id}/purchase-orders/{order_id}",
    response_model=PurchaseOrderResponse,
)
async def update_purchase_order(
    supplier_id: uuid.UUID,  # noqa: ARG001
    order_id: uuid.UUID,
    data: PurchaseOrderUpdate,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    """Update expected date or notes on a pending purchase order."""
    return await PurchaseOrderService(db, tenant_id).update_order(order_id, data)


@router.post(
    "/{supplier_id}/purchase-orders/{order_id}/receive",
    response_model=PurchaseOrderResponse,
)
async def receive_purchase_order(
    supplier_id: uuid.UUID,  # noqa: ARG001
    order_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    """Mark a purchase order as received and increment stock for each line."""
    return await PurchaseOrderService(db, tenant_id).receive_order(order_id)


@router.post(
    "/{supplier_id}/purchase-orders/{order_id}/cancel",
    response_model=PurchaseOrderResponse,
)
async def cancel_purchase_order(
    supplier_id: uuid.UUID,  # noqa: ARG001
    order_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    tenant_id: CurrentTenantId,
):
    """Cancel a pending purchase order."""
    return await PurchaseOrderService(db, tenant_id).cancel_order(order_id)
