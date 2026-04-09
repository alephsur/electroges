from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import ChangePasswordRequest, InvitationActivateRequest

# Services return (user, access_token, refresh_token) so the router can
# place the tokens in HttpOnly cookies without exposing them in the body.
type AuthTokens = tuple[User, str, str]


class AuthService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)
        self.session = session

    async def login(self, email: str, password: str) -> AuthTokens:
        user = await self.repo.get_by_email(email)
        if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cuenta pendiente de activación o desactivada",
            )
        return self._build_tokens(user)

    async def refresh(self, refresh_token: str) -> AuthTokens:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresco inválido o expirado",
            )
        user_id_str = payload.get("user_id")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresco inválido",
            )
        from uuid import UUID
        user = await self.repo.get_by_id(UUID(user_id_str))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado o desactivado",
            )
        return self._build_tokens(user)

    async def activate_invitation(self, data: InvitationActivateRequest) -> AuthTokens:
        """Activate a pending account using the invitation token and set a password."""
        user = await self.repo.get_by_invitation_token(data.token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token de invitación no válido",
            )
        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta cuenta ya está activada",
            )
        if user.invitation_expires_at and user.invitation_expires_at < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="El token de invitación ha expirado. Solicita un nuevo enlace al administrador.",
            )

        await self.repo.update(user, {
            "hashed_password": hash_password(data.password),
            "is_active": True,
            "invitation_token": None,
            "invitation_expires_at": None,
        })
        await self.session.commit()
        await self.session.refresh(user)

        return self._build_tokens(user)

    async def change_password(self, user: User, data: ChangePasswordRequest) -> None:
        if not user.hashed_password or not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña actual es incorrecta",
            )
        await self.repo.update(user, {"hashed_password": hash_password(data.new_password)})
        await self.session.commit()

    def _build_tokens(self, user: User) -> AuthTokens:
        token_data = {
            "sub": user.email,
            "user_id": str(user.id),
            "role": user.role.value,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        }
        return (
            user,
            create_access_token(token_data),
            create_refresh_token(token_data),
        )
