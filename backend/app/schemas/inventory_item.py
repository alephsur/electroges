from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.supplier_item import SupplierItemResponse


class InventoryItemCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    unit: str = Field(default="ud", max_length=20)
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    stock_current: Decimal = Field(default=Decimal("0"), ge=0)
    stock_min: Decimal = Field(default=Decimal("0"), ge=0)
    supplier_id: UUID | None = None


class InventoryItemCreateWithSupplier(BaseModel):
    """Used by the /inventory endpoint — creates an item with an optional initial supplier."""

    name: str = Field(..., max_length=255)
    description: str | None = None
    unit: str = Field(default="ud", max_length=20)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    stock_min: Decimal = Field(default=Decimal("0"), ge=0)
    is_active: bool = True
    # Optional initial supplier
    supplier_id: UUID | None = None
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)
    supplier_ref: str | None = None
    is_preferred: bool = True


class InventoryItemUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    unit: str | None = Field(default=None, max_length=20)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    stock_min: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None
    # stock_current is intentionally absent — stock is modified via movements only


class InventoryItemBrief(BaseModel):
    """Lightweight response for nested contexts (e.g. purchase order lines).
    Does not include ORM-traversal fields like supplier_items or stock_movements."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    unit: str
    unit_cost: Decimal
    unit_price: Decimal
    stock_current: Decimal
    stock_min: Decimal
    is_active: bool


class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    unit: str
    unit_cost: Decimal
    unit_cost_avg: Decimal = Decimal("0")
    unit_price: Decimal
    stock_current: Decimal
    stock_min: Decimal
    supplier_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Computed fields (populated by InventoryService._enrich_item)
    stock_reserved: Decimal = Decimal("0")
    stock_available: Decimal = Decimal("0")
    low_stock_alert: bool = False
    last_movement_at: datetime | None = None

    # Multi-supplier fields (populated by InventoryService._enrich_item)
    supplier_items: list[SupplierItemResponse] = []
    preferred_supplier: SupplierItemResponse | None = None


class InventoryItemListResponse(BaseModel):
    items: list[InventoryItemResponse]
    total: int
    skip: int
    limit: int
