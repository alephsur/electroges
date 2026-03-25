from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InventoryItemCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    unit: str = Field(default="ud", max_length=20)
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    stock_current: Decimal = Field(default=Decimal("0"), ge=0)
    stock_min: Decimal = Field(default=Decimal("0"), ge=0)
    supplier_id: UUID | None = None


class InventoryItemUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    unit: str | None = Field(default=None, max_length=20)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    stock_current: Decimal | None = Field(default=None, ge=0)
    stock_min: Decimal | None = Field(default=None, ge=0)
    supplier_id: UUID | None = None
    is_active: bool | None = None


class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    unit: str
    unit_cost: Decimal
    unit_price: Decimal
    stock_current: Decimal
    stock_min: Decimal
    supplier_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InventoryItemListResponse(BaseModel):
    items: list[InventoryItemResponse]
    total: int
    skip: int
    limit: int
