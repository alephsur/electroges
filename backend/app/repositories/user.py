import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_invitation_token(self, token: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.invitation_token == token)
        )
        return result.scalar_one_or_none()

    async def get_superadmin(self) -> User | None:
        result = await self.session.execute(
            select(User).where(User.role == UserRole.SUPERADMIN).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[User]:
        result = await self.session.execute(
            select(User).where(User.tenant_id == tenant_id)
        )
        return list(result.scalars().all())
