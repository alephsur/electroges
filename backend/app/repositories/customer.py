import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer, CustomerAddress
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(Customer, session, tenant_id)

    async def search(
        self,
        query: str | None = None,
        customer_type: str | None = None,
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Customer], int]:
        stmt = select(Customer).options(selectinload(Customer.addresses))
        count_stmt = select(func.count()).select_from(Customer)

        if self.tenant_id is not None:
            stmt = stmt.where(Customer.tenant_id == self.tenant_id)
            count_stmt = count_stmt.where(Customer.tenant_id == self.tenant_id)

        if is_active is not None:
            stmt = stmt.where(Customer.is_active == is_active)
            count_stmt = count_stmt.where(Customer.is_active == is_active)

        if customer_type is not None:
            stmt = stmt.where(Customer.customer_type == customer_type)
            count_stmt = count_stmt.where(Customer.customer_type == customer_type)

        if query:
            pattern = f"%{query}%"
            search_filter = or_(
                Customer.name.ilike(pattern),
                Customer.tax_id.ilike(pattern),
                Customer.email.ilike(pattern),
                Customer.contact_person.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        stmt = stmt.order_by(Customer.created_at.desc()).offset(skip).limit(limit)

        rows = await self.session.execute(stmt)
        total = await self.session.execute(count_stmt)

        return list(rows.scalars().all()), total.scalar_one()

    async def get_with_detail(self, customer_id: uuid.UUID) -> Customer | None:
        stmt = (
            select(Customer)
            .options(
                selectinload(Customer.addresses),
                selectinload(Customer.documents),
            )
            .where(Customer.id == customer_id)
        )
        if self.tenant_id is not None:
            stmt = stmt.where(Customer.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_tax_id(self, tax_id: str) -> Customer | None:
        stmt = select(Customer).where(Customer.tax_id == tax_id)
        if self.tenant_id is not None:
            stmt = stmt.where(Customer.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_address(self, customer_id: uuid.UUID) -> CustomerAddress | None:
        result = await self.session.execute(
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id)
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()
