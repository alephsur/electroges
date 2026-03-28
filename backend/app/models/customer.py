from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class CustomerType(str, enum.Enum):
    INDIVIDUAL = "individual"  # Particular / persona física
    COMPANY = "company"        # Empresa / persona jurídica
    COMMUNITY = "community"    # Comunidad de propietarios


class AddressType(str, enum.Enum):
    FISCAL = "fiscal"    # Dirección de facturación
    SERVICE = "service"  # Dirección donde se realiza el trabajo


class Customer(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    customer_type: Mapped[CustomerType] = mapped_column(
        SQLEnum(CustomerType, name="customertype", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=CustomerType.INDIVIDUAL,
    )
    # Full name for individuals, company name for company/community
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # NIF for individuals, CIF for companies/communities
    tax_id: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    phone_secondary: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Contact person for companies and communities
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    addresses: Mapped[list[CustomerAddress]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="CustomerAddress.is_default.desc()",
    )
    documents: Mapped[list[CustomerDocument]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="CustomerDocument.created_at.desc()",
    )
    site_visits: Mapped[list["SiteVisit"]] = relationship(
        back_populates="customer",
        order_by="SiteVisit.visit_date.desc()",
    )
    budgets: Mapped[list["Budget"]] = relationship(
        back_populates="customer",
        order_by="Budget.issue_date.desc()",
    )
    # work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="customer")


class CustomerAddress(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "customer_addresses"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    address_type: Mapped[AddressType] = mapped_column(
        SQLEnum(AddressType, name="addresstype", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=AddressType.SERVICE,
    )
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "Casa", "Portal A", etc.
    street: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(10), nullable=False)
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    customer: Mapped[Customer] = relationship(back_populates="addresses")


class CustomerDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "customer_documents"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # contract | id_document | authorization | other
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")

    customer: Mapped[Customer] = relationship(back_populates="documents")
