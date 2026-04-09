"""Base repository with generic CRUD operations and optional tenant isolation."""

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(
        self,
        model: type[ModelType],
        session: AsyncSession,
        tenant_id: uuid.UUID | None = None,
    ):
        self.model = model
        self.session = session
        self.tenant_id = tenant_id

    def _tenant_filter(self, stmt):
        """Apply tenant_id WHERE clause if this repository is tenant-scoped."""
        if self.tenant_id is not None and hasattr(self.model, "tenant_id"):
            stmt = stmt.where(self.model.tenant_id == self.tenant_id)
        return stmt

    async def get_by_id(self, record_id: uuid.UUID) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == record_id)
        stmt = self._tenant_filter(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        stmt = self._tenant_filter(stmt)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: ModelType, data: dict[str, Any]) -> ModelType:
        for key, value in data.items():
            setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        await self.session.delete(obj)
        await self.session.flush()
