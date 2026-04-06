import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer, CustomerAddress
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: AsyncSession):
        super().__init__(Customer, session)

    async def search(
        self,
        query: str | None = None,
        customer_type: str | None = None,
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Customer], int]:
        """
        Search customers with filters. Returns (items, total_count).
        query applies ilike over name, tax_id, email, contact_person.
        Eager-loads addresses to display the primary address in the list.
        """
        stmt = select(Customer).options(selectinload(Customer.addresses))
        count_stmt = select(func.count()).select_from(Customer)

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
        """
        Eager-load addresses and documents.
        Does NOT load site_visits or work_orders — those are loaded
        separately in the service for the timeline.
        """
        result = await self.session.execute(
            select(Customer)
            .options(
                selectinload(Customer.addresses),
                selectinload(Customer.documents),
            )
            .where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()

    async def get_by_tax_id(self, tax_id: str) -> Customer | None:
        """Used to validate tax_id uniqueness."""
        result = await self.session.execute(
            select(Customer).where(Customer.tax_id == tax_id)
        )
        return result.scalar_one_or_none()

    async def get_default_address(self, customer_id: uuid.UUID) -> CustomerAddress | None:
        """The address marked as is_default, or the first one if none is marked."""
        result = await self.session.execute(
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id)
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()
