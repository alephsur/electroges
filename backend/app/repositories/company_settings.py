"""Repository for CompanySettings singleton."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_settings import CompanySettings


class CompanySettingsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self) -> CompanySettings:
        """Always returns the singleton (id=1). Creates it if it does not exist."""
        result = await self.session.execute(
            select(CompanySettings).where(CompanySettings.id == 1)
        )
        settings = result.scalar_one_or_none()
        if not settings:
            settings = CompanySettings(id=1)
            self.session.add(settings)
            await self.session.flush()
            await self.session.refresh(settings)
        return settings

    async def update(self, data: dict) -> CompanySettings:
        settings = await self.get()
        for key, value in data.items():
            setattr(settings, key, value)
        await self.session.flush()
        await self.session.refresh(settings)
        return settings
