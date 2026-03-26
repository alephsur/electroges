import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import CustomerAddress
from app.repositories.base import BaseRepository


class CustomerAddressRepository(BaseRepository[CustomerAddress]):
    def __init__(self, session: AsyncSession):
        super().__init__(CustomerAddress, session)

    async def get_by_customer(self, customer_id: uuid.UUID) -> list[CustomerAddress]:
        result = await self.session.execute(
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id)
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at)
        )
        return list(result.scalars().all())

    async def set_default(self, address_id: uuid.UUID, customer_id: uuid.UUID) -> None:
        """
        Atomically deactivates is_default on all addresses for the customer
        then activates only the specified one. Two SQL UPDATEs, no Python read-modify-write.
        """
        await self.session.execute(
            update(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id)
            .values(is_default=False)
        )
        await self.session.execute(
            update(CustomerAddress)
            .where(CustomerAddress.id == address_id)
            .values(is_default=True)
        )
