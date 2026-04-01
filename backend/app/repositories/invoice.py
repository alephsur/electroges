"""Repositories for the Invoicing module."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invoice import Invoice, InvoiceLine, Payment
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    def __init__(self, session: AsyncSession):
        super().__init__(Invoice, session)

    async def get_next_invoice_number(
        self, is_rectification: bool = False
    ) -> str:
        year = datetime.now().year
        prefix = f"FAC-R-{year}-" if is_rectification else f"FAC-{year}-"
        result = await self.session.execute(
            select(func.count(Invoice.id)).where(
                Invoice.invoice_number.like(f"{prefix}%")
            )
        )
        count = result.scalar() or 0
        return f"{prefix}{(count + 1):04d}"

    async def search(
        self,
        query: str | None,
        customer_id: uuid.UUID | None,
        work_order_id: uuid.UUID | None,
        status: str | None,
        overdue_only: bool,
        date_from: date | None,
        date_to: date | None,
        skip: int,
        limit: int,
    ) -> tuple[list[Invoice], int]:
        from app.models.customer import Customer
        from app.models.work_order import WorkOrder

        stmt = select(Invoice).options(
            selectinload(Invoice.customer),
            selectinload(Invoice.work_order),
            selectinload(Invoice.payments),
            selectinload(Invoice.lines),
        )
        count_stmt = select(func.count()).select_from(Invoice)

        if customer_id is not None:
            stmt = stmt.where(Invoice.customer_id == customer_id)
            count_stmt = count_stmt.where(Invoice.customer_id == customer_id)

        if work_order_id is not None:
            stmt = stmt.where(Invoice.work_order_id == work_order_id)
            count_stmt = count_stmt.where(
                Invoice.work_order_id == work_order_id
            )

        if status is not None:
            stmt = stmt.where(Invoice.status == status)
            count_stmt = count_stmt.where(Invoice.status == status)

        if overdue_only:
            stmt = stmt.where(Invoice.status == "sent").where(
                Invoice.due_date < date.today()
            )
            count_stmt = count_stmt.where(Invoice.status == "sent").where(
                Invoice.due_date < date.today()
            )

        if date_from is not None:
            stmt = stmt.where(Invoice.issue_date >= date_from)
            count_stmt = count_stmt.where(Invoice.issue_date >= date_from)

        if date_to is not None:
            stmt = stmt.where(Invoice.issue_date <= date_to)
            count_stmt = count_stmt.where(Invoice.issue_date <= date_to)

        if query:
            search = f"%{query}%"
            stmt = stmt.join(
                Customer, Invoice.customer_id == Customer.id
            ).where(
                or_(
                    Invoice.invoice_number.ilike(search),
                    Customer.name.ilike(search),
                )
            )
            count_stmt = count_stmt.join(
                Customer, Invoice.customer_id == Customer.id
            ).where(
                or_(
                    Invoice.invoice_number.ilike(search),
                    Customer.name.ilike(search),
                )
            )

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(Invoice.issue_date.desc()).offset(skip).limit(
            limit
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_with_full_detail(
        self, invoice_id: uuid.UUID
    ) -> Invoice | None:
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .options(
                selectinload(Invoice.customer),
                selectinload(Invoice.work_order),
                selectinload(Invoice.lines),
                selectinload(Invoice.payments),
                selectinload(Invoice.rectifies_invoice),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_work_order(
        self, work_order_id: uuid.UUID
    ) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.work_order_id == work_order_id)
            .options(
                selectinload(Invoice.customer),
                selectinload(Invoice.payments),
                selectinload(Invoice.lines),
            )
            .order_by(Invoice.issue_date.desc())
        )
        return list(result.scalars().all())

    async def get_by_customer(
        self, customer_id: uuid.UUID
    ) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.customer_id == customer_id)
            .options(
                selectinload(Invoice.payments),
                selectinload(Invoice.lines),
            )
            .order_by(Invoice.issue_date.desc())
        )
        return list(result.scalars().all())

    async def get_total_invoiced_for_work_order(
        self, work_order_id: uuid.UUID
    ) -> Decimal:
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.work_order_id == work_order_id)
            .where(Invoice.status.in_(["sent", "paid"]))
            .where(Invoice.is_rectification.is_(False))
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.payments),
            )
        )
        invoices = list(result.scalars().all())
        return sum(
            self._calculate_total(inv) for inv in invoices
        )

    async def get_overdue_invoices(self) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.status == "sent")
            .where(Invoice.due_date < date.today())
            .options(
                selectinload(Invoice.customer),
                selectinload(Invoice.payments),
                selectinload(Invoice.lines),
            )
            .order_by(Invoice.due_date)
        )
        return list(result.scalars().all())

    def _calculate_total(self, invoice: Invoice) -> Decimal:
        subtotal = sum(
            (
                line.quantity * line.unit_price
                * (1 - line.line_discount_pct / 100)
                for line in invoice.lines
            ),
            Decimal("0"),
        )
        after_discount = subtotal * (1 - invoice.discount_pct / 100)
        return after_discount * (1 + invoice.tax_rate / 100)


class InvoiceLineRepository(BaseRepository[InvoiceLine]):
    def __init__(self, session: AsyncSession):
        super().__init__(InvoiceLine, session)

    async def get_by_invoice(
        self, invoice_id: uuid.UUID
    ) -> list[InvoiceLine]:
        result = await self.session.execute(
            select(InvoiceLine)
            .where(InvoiceLine.invoice_id == invoice_id)
            .order_by(InvoiceLine.sort_order)
        )
        return list(result.scalars().all())


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Payment, session)
