from uuid import UUID

from pydantic import BaseModel, field_validator

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def password_max_length(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar los 72 caracteres")
        return v


class InvitationActivateRequest(BaseModel):
    """Payload sent by invited user to activate their account and set a password."""
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def password_max_length(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar los 72 caracteres")
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_rules(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar los 72 caracteres")
        return v


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_active: bool
    role: UserRole
    tenant_id: UUID | None

    model_config = {"from_attributes": True}
