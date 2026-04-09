import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import CustomerDocument
from app.repositories.base import BaseRepository


class CustomerDocumentRepository(BaseRepository[CustomerDocument]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None):
        super().__init__(CustomerDocument, session, tenant_id)

    async def get_by_customer(self, customer_id: uuid.UUID) -> list[CustomerDocument]:
        result = await self.session.execute(
            select(CustomerDocument)
            .where(CustomerDocument.customer_id == customer_id)
            .order_by(CustomerDocument.created_at.desc())
        )
        return list(result.scalars().all())
