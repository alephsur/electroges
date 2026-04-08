from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class SiteVisitStatus(str, enum.Enum):
    SCHEDULED   = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    CANCELLED   = "cancelled"
    NO_SHOW     = "no_show"


class SiteVisit(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "site_visits"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Customer — nullable: visit can happen before customer is registered
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Hybrid address — at least one must be present
    customer_address_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_addresses.id", ondelete="SET NULL"), nullable=True
    )
    address_text: Mapped[str | None] = mapped_column(String(500))

    # Contact info (required if customer_id is NULL)
    contact_name: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(30))

    # Scheduling
    visit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estimated_duration_hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))

    status: Mapped[SiteVisitStatus] = mapped_column(
        SQLEnum(
            SiteVisitStatus,
            name="sitevisit_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=SiteVisitStatus.SCHEDULED,
    )

    # Technical content
    description: Mapped[str | None] = mapped_column(Text)
    work_scope: Mapped[str | None] = mapped_column(Text)
    technical_notes: Mapped[str | None] = mapped_column(Text)
    estimated_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    estimated_budget: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    # Relationships
    customer: Mapped[Customer | None] = relationship(back_populates="site_visits")
    customer_address: Mapped[CustomerAddress | None] = relationship()
    materials: Mapped[list[SiteVisitMaterial]] = relationship(
        back_populates="site_visit",
        cascade="all, delete-orphan",
        order_by="SiteVisitMaterial.created_at",
    )
    photos: Mapped[list[SiteVisitPhoto]] = relationship(
        back_populates="site_visit",
        cascade="all, delete-orphan",
        order_by="SiteVisitPhoto.sort_order",
    )
    documents: Mapped[list[SiteVisitDocument]] = relationship(
        back_populates="site_visit",
        cascade="all, delete-orphan",
        order_by="SiteVisitDocument.created_at",
    )
    budgets: Mapped[list["Budget"]] = relationship(
        back_populates="site_visit",
        order_by="Budget.issue_date.desc()",
    )


class SiteVisitMaterial(UUIDMixin, TimestampMixin, Base):
    """Material estimated during the visit. Can be a catalogued item or a free-text description."""

    __tablename__ = "site_visit_materials"

    site_visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("site_visits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inventory_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(500))
    estimated_qty: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20))
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    site_visit: Mapped[SiteVisit] = relationship(back_populates="materials")
    inventory_item: Mapped[InventoryItem | None] = relationship()


class SiteVisitPhoto(UUIDMixin, TimestampMixin, Base):
    """Photos taken during the technical visit."""

    __tablename__ = "site_visit_photos"

    site_visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("site_visits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    caption: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    site_visit: Mapped[SiteVisit] = relationship(back_populates="photos")


class SiteVisitDocument(UUIDMixin, TimestampMixin, Base):
    """Sketches, plans and other documents attached to the visit."""

    __tablename__ = "site_visit_documents"

    site_visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("site_visits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")

    site_visit: Mapped[SiteVisit] = relationship(back_populates="documents")
