from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class CompanySettings(TimestampMixin, Base):
    """
    Company configuration — singleton (always ID = 1).
    Used to generate PDFs for budgets and invoices.
    """

    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    company_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", server_default=""
    )
    tax_id: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(10))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    bank_account: Mapped[str | None] = mapped_column(String(50))
    logo_path: Mapped[str | None] = mapped_column(String(500))
    general_conditions: Mapped[str | None] = mapped_column(Text)
    default_tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("21.00"), server_default="21.00"
    )
    default_validity_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
