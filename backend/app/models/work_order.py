from __future__ import annotations

import enum
import uuid
from decimal import Decimal

from sqlalchemy import (
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class WorkOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PENDING_CLOSURE = "pending_closure"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CertificationStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    INVOICED = "invoiced"


class DeliveryNoteStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"


class DeliveryNoteLineType(str, enum.Enum):
    MATERIAL = "material"
    LABOR = "labor"
    OTHER = "other"


class WorkOrder(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        UniqueConstraint("tenant_id", "work_order_number", name="uq_work_orders_tenant_number"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    work_order_number: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True
    )
    origin_budget_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=True
    )
    status: Mapped[WorkOrderStatus] = mapped_column(
        SQLEnum(
            WorkOrderStatus,
            name="work_order_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=WorkOrderStatus.DRAFT,
    )
    address: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    other_lines_notes: Mapped[str | None] = mapped_column(Text)
    # Fase 2: FK a operators se añade en migración de Fase 2
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="work_orders")
    origin_budget: Mapped["Budget | None"] = relationship(
        back_populates="work_order",
        foreign_keys=[origin_budget_id],
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="Task.sort_order",
    )
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="Certification.created_at",
    )
    purchase_order_links: Mapped[list["WorkOrderPurchaseOrder"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
    )
    delivery_notes: Mapped[list["DeliveryNote"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="DeliveryNote.created_at",
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="work_order",
        order_by="Invoice.issue_date.desc()",
    )


class Task(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_orders.id"), nullable=False, index=True
    )
    origin_budget_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budget_lines.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(
            TaskStatus,
            name="task_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=TaskStatus.PENDING,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimated_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    actual_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    # Fase 2: FK a operators se añade en Fase 2
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Relationships
    work_order: Mapped["WorkOrder"] = relationship(back_populates="tasks")
    origin_budget_line: Mapped["BudgetLine | None"] = relationship(
        back_populates="task",
        foreign_keys=[origin_budget_line_id],
    )
    materials: Mapped[list["TaskMaterial"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    certification_items: Mapped[list["CertificationItem"]] = relationship(
        back_populates="task",
    )


class TaskMaterial(UUIDMixin, TimestampMixin, Base):
    """Material previsto y consumido en una tarea."""

    __tablename__ = "task_materials"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True
    )
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False
    )
    origin_budget_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budget_lines.id"), nullable=True
    )
    estimated_quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False
    )
    consumed_quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False, default=Decimal("0.0")
    )
    # Snapshot del PMP en el momento de creación
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="materials")
    inventory_item: Mapped["InventoryItem"] = relationship()
    origin_budget_line: Mapped["BudgetLine | None"] = relationship(
        back_populates="task_material",
        foreign_keys=[origin_budget_line_id],
    )


class WorkOrderPurchaseOrder(UUIDMixin, TimestampMixin, Base):
    """Relación N:N entre Obras y Pedidos a Proveedor."""

    __tablename__ = "work_order_purchase_orders"

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_orders.id"), nullable=False, index=True
    )
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False, index=True
    )
    notes: Mapped[str | None] = mapped_column(String(255))

    work_order: Mapped["WorkOrder"] = relationship(back_populates="purchase_order_links")
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        back_populates="work_order_links"
    )

    __table_args__ = (
        UniqueConstraint(
            "work_order_id", "purchase_order_id",
            name="uq_work_order_purchase_order",
        ),
    )


class Certification(UUIDMixin, TimestampMixin, Base):
    """Certificación de avance de obra basada en tareas completadas."""

    __tablename__ = "certifications"

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_orders.id"), nullable=False, index=True
    )
    certification_number: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )
    status: Mapped[CertificationStatus] = mapped_column(
        SQLEnum(
            CertificationStatus,
            name="certification_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=CertificationStatus.DRAFT,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    # FK a invoices se añade en migración de Facturación
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Relationships
    work_order: Mapped["WorkOrder"] = relationship(back_populates="certifications")
    items: Mapped[list["CertificationItem"]] = relationship(
        back_populates="certification",
        cascade="all, delete-orphan",
    )


class CertificationItem(UUIDMixin, TimestampMixin, Base):
    """Tarea certificada dentro de una certificación."""

    __tablename__ = "certification_items"

    certification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("certifications.id"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False
    )
    # Snapshot del importe en el momento de certificar
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255))

    certification: Mapped["Certification"] = relationship(back_populates="items")
    task: Mapped["Task"] = relationship(back_populates="certification_items")


class DeliveryNote(UUIDMixin, TimestampMixin, Base):
    """Albarán de entrega de materiales/trabajos en una obra."""

    __tablename__ = "delivery_notes"

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_orders.id"), nullable=False, index=True
    )
    delivery_note_number: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )
    status: Mapped[DeliveryNoteStatus] = mapped_column(
        SQLEnum(
            DeliveryNoteStatus,
            name="delivery_note_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=DeliveryNoteStatus.DRAFT,
    )
    delivery_date: Mapped[str] = mapped_column(String(10), nullable=False)  # ISO date
    requested_by: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    work_order: Mapped["WorkOrder"] = relationship(back_populates="delivery_notes")
    items: Mapped[list["DeliveryNoteItem"]] = relationship(
        back_populates="delivery_note",
        cascade="all, delete-orphan",
        order_by="DeliveryNoteItem.sort_order",
    )


class DeliveryNoteItem(UUIDMixin, TimestampMixin, Base):
    """Línea de un albarán: material, mano de obra u otros."""

    __tablename__ = "delivery_note_items"

    delivery_note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_notes.id"), nullable=False, index=True
    )
    line_type: Mapped[DeliveryNoteLineType] = mapped_column(
        SQLEnum(
            DeliveryNoteLineType,
            name="delivery_note_line_type",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=DeliveryNoteLineType.MATERIAL,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    inventory_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="ud")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    delivery_note: Mapped["DeliveryNote"] = relationship(back_populates="items")
    inventory_item: Mapped["InventoryItem | None"] = relationship()


# Resolve forward references
from app.models.budget import Budget, BudgetLine  # noqa: E402
from app.models.customer import Customer  # noqa: E402
from app.models.inventory_item import InventoryItem  # noqa: E402
from app.models.purchase_order import PurchaseOrder  # noqa: E402
from app.models.invoice import Invoice  # noqa: E402
