"""Tenant management service.

Responsibilities:
- Create tenants (superadmin only)
- Create the initial admin user for a tenant and send the invitation email
- List / update / deactivate tenants
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.email import send_invitation_email
from app.core.security import generate_invitation_token
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository
from app.schemas.tenant import TenantBranding, TenantCreate, TenantUpdate, TenantUserInvite, TenantUserUpdate

_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
_MAX_LOGO_BYTES = 5 * 1024 * 1024  # 5 MB

logger = logging.getLogger(__name__)


class TenantService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.tenant_repo = TenantRepository(session)
        self.user_repo = UserRepository(session)

    async def create_tenant(self, data: TenantCreate) -> Tenant:
        """Create a tenant and send an invitation to its first admin user."""
        # Validate admin email is not already registered
        existing_user = await self.user_repo.get_by_email(data.admin_email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un usuario con ese email",
            )

        # Create tenant
        tenant = Tenant(
            name=data.name,
            tax_id=data.tax_id,
            address=data.address,
            phone=data.phone,
            email=data.email,
        )
        tenant = await self.tenant_repo.create(tenant)

        # Create the pending admin user (no password yet — activated via invitation)
        invitation_token = generate_invitation_token()
        expires_at = datetime.now(UTC) + timedelta(hours=settings.INVITATION_EXPIRE_HOURS)

        admin_user = User(
            email=data.admin_email,
            full_name=data.admin_full_name,
            hashed_password=None,
            is_active=False,
            role=UserRole.ADMIN,
            tenant_id=tenant.id,
            invitation_token=invitation_token,
            invitation_expires_at=expires_at,
        )
        await self.user_repo.create(admin_user)
        await self.session.commit()

        # Send invitation email
        activation_url = f"{settings.FRONTEND_URL}/activate?token={invitation_token}"
        try:
            send_invitation_email(
                to_email=data.admin_email,
                full_name=data.admin_full_name,
                tenant_name=data.name,
                activation_url=activation_url,
            )
        except Exception:
            # Email failure must not roll back the tenant creation
            logger.error(
                "Failed to send invitation email to %s for tenant %s",
                data.admin_email,
                tenant.id,
            )

        logger.info(
            "Tenant created: id=%s name=%s admin=%s invitation_token=%s",
            tenant.id,
            tenant.name,
            data.admin_email,
            invitation_token,
        )
        return await self.tenant_repo.get_with_users(tenant.id)

    async def list_tenants(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        return await self.tenant_repo.list_with_users(skip=skip, limit=limit)

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self.tenant_repo.get_with_users(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant no encontrado",
            )
        return tenant

    async def update_tenant(self, tenant_id: uuid.UUID, data: TenantUpdate) -> Tenant:
        tenant = await self.get_tenant(tenant_id)
        update_data = data.model_dump(exclude_none=True)
        tenant = await self.tenant_repo.update(tenant, update_data)
        await self.session.commit()
        return await self.tenant_repo.get_with_users(tenant_id)

    async def deactivate_tenant(self, tenant_id: uuid.UUID) -> None:
        tenant = await self.get_tenant(tenant_id)
        await self.tenant_repo.update(tenant, {"is_active": False})
        await self.session.commit()

    async def get_branding(self, user: User) -> TenantBranding:
        """Return the branding (name + logo) for the current user's tenant."""
        if not user.tenant_id:
            # Superadmin: return application default
            return TenantBranding(name=settings.APP_NAME, logo_url=None)

        tenant = await self.tenant_repo.get_by_id(user.tenant_id)
        if not tenant:
            return TenantBranding(name=settings.APP_NAME, logo_url=None)

        return TenantBranding(name=tenant.name, logo_url=tenant.logo_url)

    async def upload_logo(self, tenant_id: uuid.UUID, file: UploadFile) -> Tenant:
        """Save an uploaded logo for the given tenant and update logo_url."""
        tenant = await self.get_tenant(tenant_id)

        if file.content_type not in _ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Formato de imagen no válido. Usa PNG, JPG, GIF, WebP o SVG.",
            )

        contents = await file.read()
        if len(contents) > _MAX_LOGO_BYTES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El archivo supera el tamaño máximo permitido (5 MB).",
            )

        suffix = Path(file.filename or "logo").suffix or ".png"
        logo_dir = Path(settings.UPLOAD_DIR) / "logos" / str(tenant_id)
        logo_dir.mkdir(parents=True, exist_ok=True)
        logo_path = logo_dir / f"logo{suffix}"
        logo_path.write_bytes(contents)

        logo_url = f"/uploads/logos/{tenant_id}/logo{suffix}"
        await self.tenant_repo.update(tenant, {"logo_url": logo_url})
        await self.session.commit()

        return await self.tenant_repo.get_with_users(tenant_id)

    async def invite_user(self, tenant_id: uuid.UUID, data: TenantUserInvite) -> User:
        """Invite a new user to an existing tenant."""
        tenant = await self.get_tenant(tenant_id)

        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un usuario con ese email",
            )

        invitation_token = generate_invitation_token()
        expires_at = datetime.now(UTC) + timedelta(hours=settings.INVITATION_EXPIRE_HOURS)
        role = UserRole.ADMIN if data.role == "admin" else UserRole.USER

        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=None,
            is_active=False,
            role=role,
            tenant_id=tenant_id,
            invitation_token=invitation_token,
            invitation_expires_at=expires_at,
        )
        await self.user_repo.create(user)
        await self.session.commit()

        activation_url = f"{settings.FRONTEND_URL}/activate?token={invitation_token}"
        try:
            send_invitation_email(
                to_email=data.email,
                full_name=data.full_name,
                tenant_name=tenant.name,
                activation_url=activation_url,
            )
        except Exception:
            logger.error(
                "Failed to send invitation email to %s for tenant %s",
                data.email,
                tenant_id,
            )

        logger.info(
            "User invited: email=%s role=%s tenant=%s token=%s",
            data.email,
            data.role,
            tenant_id,
            invitation_token,
        )
        return user

    async def update_tenant_user(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, data: TenantUserUpdate
    ) -> User:
        """Update a tenant user's role or active status."""
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado en este tenant",
            )

        update_data: dict = {}
        if data.role is not None:
            update_data["role"] = UserRole.ADMIN if data.role == "admin" else UserRole.USER
        if data.is_active is not None:
            update_data["is_active"] = data.is_active

        if update_data:
            await self.user_repo.update(user, update_data)
            await self.session.commit()

        return await self.user_repo.get_by_id(user_id)

    async def deactivate_tenant_user(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Deactivate a user within a tenant."""
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado en este tenant",
            )

        await self.user_repo.update(user, {"is_active": False})
        await self.session.commit()

    async def resend_invitation(self, user_id: uuid.UUID) -> None:
        """Regenerate the invitation token and resend the email."""
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario pendiente de activación no encontrado",
            )

        tenant = await self.tenant_repo.get_by_id(user.tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant no encontrado")

        new_token = generate_invitation_token()
        new_expires = datetime.now(UTC) + timedelta(hours=settings.INVITATION_EXPIRE_HOURS)
        await self.user_repo.update(user, {
            "invitation_token": new_token,
            "invitation_expires_at": new_expires,
        })
        await self.session.commit()

        activation_url = f"{settings.FRONTEND_URL}/activate?token={new_token}"
        send_invitation_email(
            to_email=user.email,
            full_name=user.full_name,
            tenant_name=tenant.name,
            activation_url=activation_url,
        )
