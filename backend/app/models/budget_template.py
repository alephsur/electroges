"""Reusable budget templates (e.g. 'Instalación base vivienda 90m²')."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.budget import BudgetLineType


class BudgetTemplate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "budget_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_budget_templates_tenant_name"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    sections: Mapped[list["BudgetTemplateSection"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="BudgetTemplateSection.sort_order",
    )
    lines: Mapped[list["BudgetTemplateLine"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="BudgetTemplateLine.sort_order",
    )


class BudgetTemplateSection(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "budget_template_sections"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budget_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    template: Mapped[BudgetTemplate] = relationship(back_populates="sections")
    lines: Mapped[list["BudgetTemplateLine"]] = relationship(
        back_populates="section",
        order_by="BudgetTemplateLine.sort_order",
    )


class BudgetTemplateLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "budget_template_lines"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budget_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("budget_template_sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    line_type: Mapped[BudgetLineType] = mapped_column(
        SQLEnum(
            BudgetLineType,
            name="budget_line_type",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    inventory_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0.0"), server_default="0.0"
    )
    line_discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )

    template: Mapped[BudgetTemplate] = relationship(back_populates="lines")
    section: Mapped["BudgetTemplateSection | None"] = relationship(
        back_populates="lines"
    )
