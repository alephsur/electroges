"""Repository for CompanySettings — one record per tenant."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.company_settings import CompanySettings


class CompanySettingsRepository:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def get(self) -> CompanySettings:
        """Return the settings for the current tenant. Creates defaults if missing."""
        result = await self.session.execute(
            select(CompanySettings)
            .options(joinedload(CompanySettings.tenant))
            .where(CompanySettings.tenant_id == self.tenant_id)
        )
        company_settings = result.scalar_one_or_none()
        if not company_settings:
            company_settings = CompanySettings(tenant_id=self.tenant_id)
            self.session.add(company_settings)
            await self.session.flush()
            await self.session.refresh(company_settings)
        return company_settings

    async def update(self, data: dict) -> CompanySettings:
        company_settings = await self.get()
        for key, value in data.items():
            setattr(company_settings, key, value)
        await self.session.flush()
        await self.session.refresh(company_settings)
        return company_settings
