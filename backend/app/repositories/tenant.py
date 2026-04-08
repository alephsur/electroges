from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tenant import Tenant
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    def __init__(self, session: AsyncSession):
        super().__init__(Tenant, session)

    async def get_by_name(self, name: str) -> Tenant | None:
        result = await self.session.execute(select(Tenant).where(Tenant.name == name))
        return result.scalar_one_or_none()

    async def get_with_users(self, tenant_id) -> Tenant | None:
        result = await self.session.execute(
            select(Tenant)
            .options(selectinload(Tenant.users))
            .where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_with_users(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        result = await self.session.execute(
            select(Tenant)
            .options(selectinload(Tenant.users))
            .offset(skip)
            .limit(limit)
            .order_by(Tenant.name)
        )
        return list(result.scalars().all())
