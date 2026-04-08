from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.stock_movement import StockMovement
    from app.models.supplier import Supplier
    from app.models.supplier_item import SupplierItem


class InventoryItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "inventory_items"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="ud", server_default="ud")
    # TODO: deprecated. Use supplier_items relationship. Remove in Phase 2.
    # Kept for FK compatibility with legacy code; logic now goes through SupplierItem.
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    # Weighted average cost (PMP) — recalculated on every entry movement
    unit_cost_avg: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    stock_current: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False, default=Decimal("0"), server_default="0"
    )
    stock_min: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False, default=Decimal("0"), server_default="0"
    )
    # Maintained atomically by WorkOrder module: sum of estimated_quantity
    # of active TaskMaterials. Updated on task/work_order create/cancel.
    stock_reserved: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False, default=Decimal("0"), server_default="0"
    )
    # TODO: deprecated. Use supplier_items relationship. Remove in Phase 2.
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    supplier: Mapped[Supplier | None] = relationship("Supplier", back_populates="inventory_items")
    supplier_items: Mapped[list[SupplierItem]] = relationship(
        "SupplierItem", back_populates="inventory_item", cascade="all, delete-orphan"
    )
    stock_movements: Mapped[list[StockMovement]] = relationship(
        "StockMovement",
        back_populates="inventory_item",
        order_by="StockMovement.created_at.desc()",
    )
