from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _ResponseBase(BaseModel):
    """Base for all response schemas."""

    model_config = ConfigDict(from_attributes=True)


# ── Lines ─────────────────────────────────────────────────────────────────────

class BudgetLineCreate(BaseModel):
    line_type: Literal["labor", "material", "other"]
    description: str
    inventory_item_id: UUID | None = None
    quantity: Decimal = Field(gt=0)
    unit: str | None = None
    unit_price: Decimal = Field(ge=0)
    unit_cost: Decimal = Field(ge=0, default=Decimal("0.0"))
    line_discount_pct: Decimal = Field(ge=0, le=100, default=Decimal("0.00"))
    sort_order: int = 0


class BudgetLineUpdate(BaseModel):
    description: str | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = None
    unit_price: Decimal | None = Field(default=None, ge=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    line_discount_pct: Decimal | None = Field(default=None, ge=0, le=100)
    sort_order: int | None = None


class BudgetLinePublicResponse(_ResponseBase):
    """Schema without unit_cost or margin — for PDF and client-facing views."""

    id: UUID
    line_type: str
    sort_order: int
    description: str
    inventory_item_id: UUID | None
    inventory_item_name: str | None
    quantity: float
    unit: str | None
    unit_price: float
    line_discount_pct: float
    subtotal: float  # quantity * unit_price * (1 - discount/100)


class BudgetLineInternalResponse(BudgetLinePublicResponse):
    """Full schema with cost data — only for internal UI."""

    unit_cost: float
    margin_pct: float  # (unit_price - unit_cost) / unit_price * 100
    margin_amount: float  # (unit_price - unit_cost) * quantity


# ── Totals ────────────────────────────────────────────────────────────────────

class BudgetTotals(_ResponseBase):
    """Economic totals — always calculated at runtime, never persisted."""

    subtotal_before_discount: float
    discount_amount: float
    taxable_base: float
    tax_amount: float
    total: float
    # Internal — never include in public response
    total_cost: float
    gross_margin: float
    gross_margin_pct: float
    # Margin traffic light — internal UI only
    margin_status: Literal["red", "amber", "green"]


# ── Budget ────────────────────────────────────────────────────────────────────

class BudgetCreate(BaseModel):
    customer_id: UUID | None = None
    site_visit_id: UUID | None = None
    issue_date: date | None = None
    valid_until: date | None = None
    tax_rate: Decimal | None = None
    discount_pct: Decimal = Field(ge=0, le=100, default=Decimal("0.00"))
    notes: str | None = None
    client_notes: str | None = None
    lines: list[BudgetLineCreate] = []


class BudgetFromVisitRequest(BaseModel):
    """
    Create budget from a completed site visit.
    Visit materials are preloaded as lines automatically.
    """

    site_visit_id: UUID
    lines_override: list[BudgetLineCreate] | None = None
    tax_rate: Decimal | None = None
    discount_pct: Decimal = Decimal("0.00")
    valid_until: date | None = None
    notes: str | None = None
    client_notes: str | None = None


class BudgetUpdate(BaseModel):
    """Only editable when status=draft."""

    issue_date: date | None = None
    valid_until: date | None = None
    tax_rate: Decimal | None = None
    discount_pct: Decimal | None = Field(default=None, ge=0, le=100)
    notes: str | None = None
    client_notes: str | None = None


class BudgetStatusUpdate(BaseModel):
    status: Literal["sent", "rejected"]
    notes: str | None = None


class BudgetVersionInfo(_ResponseBase):
    id: UUID
    version: int
    budget_number: str
    status: str
    effective_status: str
    issue_date: date
    total: float
    is_latest_version: bool


class BudgetSummary(_ResponseBase):
    id: UUID
    budget_number: str
    version: int
    is_latest_version: bool
    customer_id: UUID | None
    customer_name: str | None
    site_visit_id: UUID | None
    status: str
    effective_status: str
    issue_date: date
    valid_until: date
    discount_pct: float
    tax_rate: float
    total: float
    gross_margin_pct: float
    margin_status: str
    lines_count: int
    has_pdf: bool
    created_at: datetime


class BudgetResponse(BudgetSummary):
    parent_budget_id: UUID | None
    work_order_id: UUID | None
    notes: str | None
    client_notes: str | None
    lines: list[BudgetLineInternalResponse] = []
    totals: BudgetTotals
    versions: list[BudgetVersionInfo] = []
    updated_at: datetime


class BudgetListResponse(BaseModel):
    items: list[BudgetSummary]
    total: int
    skip: int
    limit: int


class WorkOrderPreview(_ResponseBase):
    """
    Preview of the work order that would be created when accepting the budget.
    Shown to the user for confirmation BEFORE creating the work order.
    """

    budget_id: UUID
    budget_number: str
    customer_name: str | None
    tasks_to_create: list[dict]
    materials_to_reserve: list[dict]
    total_estimated_cost: float


class ReorderLinesRequest(BaseModel):
    line_ids: list[UUID]
