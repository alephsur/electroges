from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.schemas.inventory_item import InventoryItemBrief


class PurchaseOrderLineCreate(BaseModel):
    inventory_item_id: UUID | None = None
    description: str | None = Field(default=None, max_length=255)
    quantity: Decimal = Field(..., gt=0)
    unit_cost: Decimal = Field(..., ge=0)

    @model_validator(mode="after")
    def require_item_or_description(self) -> "PurchaseOrderLineCreate":
        if self.inventory_item_id is None and not self.description:
            raise ValueError("Se requiere un artículo de inventario o una descripción")
        return self


class PurchaseOrderCreate(BaseModel):
    supplier_id: UUID
    order_date: date
    expected_date: date | None = None
    notes: str | None = None
    lines: list[PurchaseOrderLineCreate] = Field(..., min_length=1)


class PurchaseOrderUpdate(BaseModel):
    expected_date: date | None = None
    notes: str | None = None


class PurchaseOrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    purchase_order_id: UUID
    inventory_item_id: UUID | None
    description: str | None
    quantity: float
    unit_cost: float
    subtotal: float
    inventory_item: InventoryItemBrief | None = None
    created_at: datetime
    updated_at: datetime


class PurchaseOrderSummary(BaseModel):
    """Lightweight response for list views — total precomputed by the repository."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supplier_id: UUID
    order_number: str
    status: str
    order_date: date
    expected_date: date | None
    received_date: date | None
    created_at: datetime
    updated_at: datetime
    # Populated by the repository via a correlated subquery — not an ORM column
    total: float = 0.0


class PurchaseOrderListResponse(BaseModel):
    items: list[PurchaseOrderSummary]
    total: int
    skip: int
    limit: int


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supplier_id: UUID
    order_number: str
    status: str
    order_date: date
    expected_date: date | None
    received_date: date | None
    notes: str | None
    lines: list[PurchaseOrderLineResponse] = []
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def total(self) -> float:
        return sum(line.subtotal for line in self.lines)
