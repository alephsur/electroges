from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.inventory_item import InventoryItem
    from app.models.supplier import Supplier


class SupplierItem(UUIDMixin, TimestampMixin, Base):
    """Intermediate table modelling the N:N relation between Supplier and InventoryItem
    with commercial context per supplier (price, reference, lead time)."""

    __tablename__ = "supplier_items"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False, index=True
    )
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False, index=True
    )
    supplier_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Unit cost charged by this supplier (updated on each received purchase order)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    # Last price actually paid (from PurchaseOrderLine)
    last_purchase_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    last_purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Only one preferred supplier per item (enforced in service layer)
    is_preferred: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    supplier: Mapped[Supplier] = relationship(back_populates="supplier_items")
    inventory_item: Mapped[InventoryItem] = relationship(back_populates="supplier_items")

    __table_args__ = (
        UniqueConstraint("supplier_id", "inventory_item_id", name="uq_supplier_item"),
    )
