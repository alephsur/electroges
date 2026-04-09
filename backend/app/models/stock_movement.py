from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.inventory_item import InventoryItem

# movement_type values: "entry" | "exit"
# reference_type values: "purchase_order" | "work_order" | "manual_adjustment"


class StockMovement(UUIDMixin, TimestampMixin, Base):
    """Immutable record of every stock change for an InventoryItem.
    Movements are never edited or deleted — corrections are new counter-movements."""

    __tablename__ = "stock_movements"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)  # entry | exit
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    reference_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # purchase_order | work_order | manual_adjustment
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    inventory_item: Mapped[InventoryItem] = relationship(back_populates="stock_movements")
