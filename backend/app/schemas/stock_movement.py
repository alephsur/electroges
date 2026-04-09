from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StockMovementCreate(BaseModel):
    inventory_item_id: UUID
    movement_type: Literal["entry", "exit"]
    quantity: Decimal = Field(gt=0)  # always positive; type determines direction
    unit_cost: Decimal = Field(gt=0)
    reference_type: Literal["purchase_order", "work_order", "manual_adjustment"]
    reference_id: UUID | None = None
    notes: str | None = None


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inventory_item_id: UUID
    inventory_item_name: str  # populated from the inventory_item relationship
    movement_type: str
    quantity: Decimal
    unit_cost: Decimal
    reference_type: str
    reference_id: UUID | None
    notes: str | None
    created_at: datetime


class ManualAdjustmentRequest(BaseModel):
    # Positive = stock entry, negative = downward correction
    quantity: Decimal = Field(description="Positive for entry, negative for correction")
    unit_cost: Decimal = Field(gt=0)
    notes: str = Field(min_length=5, description="Required for traceability")

    @field_validator("quantity")
    @classmethod
    def quantity_cannot_be_zero(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("La cantidad no puede ser cero")
        return v
