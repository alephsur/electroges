from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.inventory_item import InventoryItem
    from app.models.purchase_order import PurchaseOrder
    from app.models.supplier_item import SupplierItem


class Supplier(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    inventory_items: Mapped[list[InventoryItem]] = relationship(
        "InventoryItem", back_populates="supplier"
    )
    purchase_orders: Mapped[list[PurchaseOrder]] = relationship(
        "PurchaseOrder", back_populates="supplier", order_by="PurchaseOrder.order_date.desc()"
    )
    supplier_items: Mapped[list[SupplierItem]] = relationship(
        "SupplierItem", back_populates="supplier"
    )
