from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class BudgetStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"  # Calculated at runtime — never persisted


class BudgetLineType(str, enum.Enum):
    LABOR = "labor"
    MATERIAL = "material"
    OTHER = "other"


class Budget(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "budgets"

    # Auto-numbering: PRES-2025-0001
    budget_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    # Versioning — Model A: each version is an independent Budget
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    parent_budget_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=True
    )
    is_latest_version: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # Origin — customer required, site_visit optional
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True
    )
    site_visit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("site_visits.id"), nullable=True
    )

    status: Mapped[BudgetStatus] = mapped_column(
        SQLEnum(
            BudgetStatus,
            name="budget_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=BudgetStatus.DRAFT,
    )

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)

    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("21.00"), server_default="21.00"
    )
    discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )

    notes: Mapped[str | None] = mapped_column(Text)
    client_notes: Mapped[str | None] = mapped_column(Text)
    pdf_path: Mapped[str | None] = mapped_column(String(500))

    # FK to WorkOrder — constraint added in WorkOrder migration
    work_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Relationships
    customer: Mapped[Customer] = relationship(back_populates="budgets")
    site_visit: Mapped[SiteVisit | None] = relationship(back_populates="budgets")
    lines: Mapped[list[BudgetLine]] = relationship(
        back_populates="budget",
        cascade="all, delete-orphan",
        order_by="BudgetLine.sort_order",
    )
    parent_budget: Mapped[Budget | None] = relationship(
        remote_side="Budget.id",
        foreign_keys=[parent_budget_id],
        back_populates="child_budgets",
    )
    child_budgets: Mapped[list[Budget]] = relationship(
        back_populates="parent_budget",
        foreign_keys=[parent_budget_id],
    )
    work_order: Mapped["WorkOrder | None"] = relationship(
        back_populates="origin_budget",
        foreign_keys="WorkOrder.origin_budget_id",
    )


class BudgetLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "budget_lines"

    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False, index=True
    )
    line_type: Mapped[BudgetLineType] = mapped_column(
        SQLEnum(
            BudgetLineType,
            name="budget_line_type",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Only for type=material — FK to inventory
    inventory_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=True
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20))

    # Sale price — visible to client and in PDF
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    # Cost price — INTERNAL, never expose in PDF or public schemas
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0.0"), server_default="0.0"
    )

    # Per-line discount (optional, additional to global discount)
    line_discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )

    # Relationships
    budget: Mapped[Budget] = relationship(back_populates="lines")
    inventory_item: Mapped[InventoryItem | None] = relationship()

    task: Mapped["Task | None"] = relationship(
        back_populates="origin_budget_line",
        foreign_keys="Task.origin_budget_line_id",
    )
    task_material: Mapped["TaskMaterial | None"] = relationship(
        back_populates="origin_budget_line",
        foreign_keys="TaskMaterial.origin_budget_line_id",
    )


# Resolve forward references
from app.models.customer import Customer  # noqa: E402
from app.models.site_visit import SiteVisit  # noqa: E402
from app.models.inventory_item import InventoryItem  # noqa: E402
