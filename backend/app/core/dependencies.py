import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

DbSession = Annotated[AsyncSession, Depends(get_db)]

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudo validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


async def _get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise _credentials_exception

    user_id_str: str | None = payload.get("user_id")
    if not user_id_str:
        raise _credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise _credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o desactivado",
        )
    return user


CurrentUser = Annotated[User, Depends(_get_current_user)]


async def _require_superadmin(current_user: CurrentUser) -> User:
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de superadministrador",
        )
    return current_user


SuperAdminUser = Annotated[User, Depends(_require_superadmin)]


async def _require_tenant_admin(current_user: CurrentUser) -> User:
    if current_user.role not in (UserRole.SUPERADMIN, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return current_user


TenantAdminUser = Annotated[User, Depends(_require_tenant_admin)]


async def _get_current_tenant_id(current_user: CurrentUser) -> uuid.UUID:
    """Return the tenant_id of the current user. Fails if user has no tenant (superadmin)."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operación requiere un tenant asociado",
        )
    return current_user.tenant_id


CurrentTenantId = Annotated[uuid.UUID, Depends(_get_current_tenant_id)]
