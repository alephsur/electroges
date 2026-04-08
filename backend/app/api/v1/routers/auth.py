from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.auth import (
    InvitationActivateRequest,
    LoginRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/token", response_model=TokenResponse)
async def login(data: LoginRequest, db: DbSession):
    """Return access and refresh tokens for valid credentials."""
    service = AuthService(db)
    return await service.login(data.email, data.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: TokenRefreshRequest, db: DbSession):
    """Return a new access token using a valid refresh token."""
    service = AuthService(db)
    return await service.refresh(data.refresh_token)


@router.post("/activate", response_model=TokenResponse)
async def activate_invitation(data: InvitationActivateRequest, db: DbSession):
    """Activate a pending account using an invitation token and set a password."""
    service = AuthService(db)
    return await service.activate_invitation(data)


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: CurrentUser):
    """Return the currently authenticated user."""
    return current_user
