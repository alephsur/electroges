from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SupplierItemCreate(BaseModel):
    supplier_id: UUID
    inventory_item_id: UUID
    unit_cost: Decimal = Field(gt=0)
    supplier_ref: str | None = None
    lead_time_days: int | None = Field(default=None, ge=1)
    is_preferred: bool = False


class SupplierItemUpdate(BaseModel):
    unit_cost: Decimal | None = Field(default=None, gt=0)
    supplier_ref: str | None = None
    lead_time_days: int | None = Field(default=None, ge=1)
    is_preferred: bool | None = None
    is_active: bool | None = None


class SupplierItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supplier_id: UUID
    supplier_name: str  # populated from the supplier relationship
    inventory_item_id: UUID
    supplier_ref: str | None
    unit_cost: float
    last_purchase_cost: float | None
    last_purchase_date: date | None
    lead_time_days: int | None
    is_preferred: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
