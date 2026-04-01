from __future__ import annotations

import enum
import uuid
from decimal import Decimal
from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    CANCELLED = "cancelled"


class InvoiceLineOrigin(str, enum.Enum):
    CERTIFICATION = "certification"
    TASK = "task"
    MANUAL = "manual"


class PaymentMethod(str, enum.Enum):
    TRANSFER = "transfer"
    CASH = "cash"
    CARD = "card"
    DIRECT_DEBIT = "direct_debit"


class Invoice(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "invoices"

    invoice_number: Mapped[str] = mapped_column(
        String(25), unique=True, nullable=False
    )
    is_rectification: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    rectifies_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True
    )
    work_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_orders.id"), nullable=True, index=True
    )

    status: Mapped[InvoiceStatus] = mapped_column(
        SQLEnum(
            InvoiceStatus,
            name="invoice_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=InvoiceStatus.DRAFT,
    )

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("21.00")
    )
    discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )

    notes: Mapped[str | None] = mapped_column(Text)
    client_notes: Mapped[str | None] = mapped_column(Text)
    pdf_path: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="invoices")
    work_order: Mapped["WorkOrder | None"] = relationship(
        back_populates="invoices"
    )
    rectifies_invoice: Mapped["Invoice | None"] = relationship(
        remote_side="Invoice.id",
        foreign_keys=[rectifies_invoice_id],
    )
    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.sort_order",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="Payment.payment_date",
    )


class InvoiceLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "invoice_lines"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False, index=True
    )
    origin_type: Mapped[InvoiceLineOrigin] = mapped_column(
        SQLEnum(
            InvoiceLineOrigin,
            name="invoice_line_origin",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=InvoiceLineOrigin.MANUAL,
    )
    origin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    line_discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )

    invoice: Mapped["Invoice"] = relationship(back_populates="lines")


class Payment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        SQLEnum(
            PaymentMethod,
            name="payment_method",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    reference: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(String(255))

    invoice: Mapped["Invoice"] = relationship(back_populates="payments")


# Resolve forward references
from app.models.customer import Customer  # noqa: E402
from app.models.work_order import WorkOrder  # noqa: E402
