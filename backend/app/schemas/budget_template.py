"""Pydantic schemas for reusable budget templates."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _ResponseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Lines ─────────────────────────────────────────────────────────────────────

class BudgetTemplateLineCreate(BaseModel):
    line_type: Literal["labor", "material", "other"]
    description: str = Field(min_length=1, max_length=500)
    section_index: int | None = None  # Index into template.sections (payload-local)
    inventory_item_id: UUID | None = None
    quantity: Decimal = Field(gt=0)
    unit: str | None = None
    unit_price: Decimal = Field(ge=0)
    unit_cost: Decimal = Field(ge=0, default=Decimal("0.0"))
    line_discount_pct: Decimal = Field(ge=0, le=100, default=Decimal("0.00"))
    sort_order: int = 0


class BudgetTemplateLineResponse(_ResponseBase):
    id: UUID
    template_id: UUID
    section_id: UUID | None
    line_type: str
    sort_order: int
    description: str
    inventory_item_id: UUID | None
    quantity: float
    unit: str | None
    unit_price: float
    unit_cost: float
    line_discount_pct: float


# ── Sections ──────────────────────────────────────────────────────────────────

class BudgetTemplateSectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    notes: str | None = None
    sort_order: int = 0


class BudgetTemplateSectionResponse(_ResponseBase):
    id: UUID
    template_id: UUID
    name: str
    notes: str | None
    sort_order: int


# ── Template ──────────────────────────────────────────────────────────────────

class BudgetTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    sections: list[BudgetTemplateSectionCreate] = []
    lines: list[BudgetTemplateLineCreate] = []


class BudgetTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class BudgetTemplateSummary(_ResponseBase):
    id: UUID
    name: str
    description: str | None
    sections_count: int
    lines_count: int
    estimated_total: float
    created_at: datetime
    updated_at: datetime


class BudgetTemplateResponse(BudgetTemplateSummary):
    sections: list[BudgetTemplateSectionResponse] = []
    lines: list[BudgetTemplateLineResponse] = []


class BudgetTemplateListResponse(BaseModel):
    items: list[BudgetTemplateSummary]
    total: int


# ── Apply to budget ───────────────────────────────────────────────────────────

class ApplyTemplateRequest(BaseModel):
    """Apply a template to an existing draft budget."""

    template_id: UUID
    mode: Literal["append", "replace"] = "append"
