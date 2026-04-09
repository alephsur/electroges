from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr


class TenantCreate(BaseModel):
    name: str
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    # Admin user that will be created for this tenant
    admin_email: EmailStr
    admin_full_name: str


class TenantUserInfo(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_active: bool
    role: str
    invitation_expires_at: datetime | None

    model_config = {"from_attributes": True}


# Kept as alias for backwards compatibility
TenantAdminInfo = TenantUserInfo


class TenantResponse(BaseModel):
    id: UUID
    name: str
    tax_id: str | None
    address: str | None
    phone: str | None
    email: str | None
    is_active: bool
    logo_url: str | None = None
    users: list[TenantUserInfo] = []

    model_config = {"from_attributes": True}


class TenantBranding(BaseModel):
    name: str
    logo_url: str | None = None


class TenantUpdate(BaseModel):
    name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool | None = None


class TenantUserInvite(BaseModel):
    email: EmailStr
    full_name: str
    role: Literal["admin", "user"] = "user"


class TenantUserUpdate(BaseModel):
    role: Literal["admin", "user"] | None = None
    is_active: bool | None = None
