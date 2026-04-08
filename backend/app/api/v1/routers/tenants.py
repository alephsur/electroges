"""Tenant management endpoints — superadmin only."""

import uuid

from fastapi import APIRouter, UploadFile, File, status

from app.core.dependencies import CurrentUser, DbSession, SuperAdminUser
from app.repositories.company_settings import CompanySettingsRepository
from app.schemas.company_settings import CompanySettingsResponse, CompanySettingsUpdate
from app.schemas.tenant import TenantBranding, TenantCreate, TenantResponse, TenantUpdate, TenantUserInfo, TenantUserInvite, TenantUserUpdate
from app.services.tenant import TenantService

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get("/branding", response_model=TenantBranding)
async def get_tenant_branding(current_user: CurrentUser, db: DbSession):
    """Return the current user's tenant name and logo URL for sidebar display.
    Superadmin users receive the default application branding."""
    service = TenantService(db)
    return await service.get_branding(current_user)


@router.post("/", response_model=TenantResponse, status_code=201)
async def create_tenant(data: TenantCreate, _: SuperAdminUser, db: DbSession):
    """Create a new tenant and send an invitation to its admin user."""
    service = TenantService(db)
    return await service.create_tenant(data)


@router.get("/", response_model=list[TenantResponse])
async def list_tenants(_: SuperAdminUser, db: DbSession, skip: int = 0, limit: int = 100):
    """List all tenants with their admin users."""
    service = TenantService(db)
    return await service.list_tenants(skip=skip, limit=limit)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: uuid.UUID, _: SuperAdminUser, db: DbSession):
    """Get a single tenant by ID."""
    service = TenantService(db)
    return await service.get_tenant(tenant_id)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id: uuid.UUID, data: TenantUpdate, _: SuperAdminUser, db: DbSession):
    """Update tenant details."""
    service = TenantService(db)
    return await service.update_tenant(tenant_id, data)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_tenant(tenant_id: uuid.UUID, _: SuperAdminUser, db: DbSession):
    """Deactivate a tenant (soft delete — sets is_active = False)."""
    service = TenantService(db)
    await service.deactivate_tenant(tenant_id)


@router.post("/{tenant_id}/logo", response_model=TenantResponse)
async def upload_tenant_logo(
    tenant_id: uuid.UUID,
    _: SuperAdminUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    """Upload or replace a tenant's logo image."""
    service = TenantService(db)
    return await service.upload_logo(tenant_id, file)


@router.post("/{tenant_id}/users", response_model=TenantUserInfo, status_code=201)
async def invite_user_to_tenant(
    tenant_id: uuid.UUID, data: TenantUserInvite, _: SuperAdminUser, db: DbSession
):
    """Invite a new user to a tenant with a specified role."""
    service = TenantService(db)
    return await service.invite_user(tenant_id, data)


@router.patch("/{tenant_id}/users/{user_id}", response_model=TenantUserInfo)
async def update_tenant_user(
    tenant_id: uuid.UUID, user_id: uuid.UUID, data: TenantUserUpdate, _: SuperAdminUser, db: DbSession
):
    """Update a tenant user's role or active status."""
    service = TenantService(db)
    return await service.update_tenant_user(tenant_id, user_id, data)


@router.delete("/{tenant_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_tenant_user(
    tenant_id: uuid.UUID, user_id: uuid.UUID, _: SuperAdminUser, db: DbSession
):
    """Deactivate a user within a tenant."""
    service = TenantService(db)
    await service.deactivate_tenant_user(tenant_id, user_id)


@router.post("/{tenant_id}/users/{user_id}/resend-invitation", status_code=204)
async def resend_invitation(tenant_id: uuid.UUID, user_id: uuid.UUID, _: SuperAdminUser, db: DbSession):
    """Regenerate and resend the invitation email for a pending user."""
    service = TenantService(db)
    await service.resend_invitation(user_id)


@router.get("/{tenant_id}/company-settings", response_model=CompanySettingsResponse)
async def get_tenant_company_settings(tenant_id: uuid.UUID, _: SuperAdminUser, db: DbSession):
    """Get the company settings for a specific tenant."""
    repo = CompanySettingsRepository(db, tenant_id)
    return await repo.get()


@router.patch("/{tenant_id}/company-settings", response_model=CompanySettingsResponse)
async def update_tenant_company_settings(
    tenant_id: uuid.UUID, data: CompanySettingsUpdate, _: SuperAdminUser, db: DbSession
):
    """Update the company settings for a specific tenant."""
    repo = CompanySettingsRepository(db, tenant_id)
    settings = await repo.update(data.model_dump(exclude_none=True))
    await db.commit()
    return settings
