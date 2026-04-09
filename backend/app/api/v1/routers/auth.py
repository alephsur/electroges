from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.config import settings
from app.core.dependencies import CurrentUser, DbSession
from app.core.rate_limiter import activation_limiter, get_client_ip, login_limiter
from app.schemas.auth import (
    InvitationActivateRequest,
    LoginRequest,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticación"])

_ACCESS_COOKIE = "access_token"
_REFRESH_COOKIE = "refresh_token"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Write both JWT tokens as HttpOnly cookies."""
    base = dict(
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        key=_ACCESS_COOKIE,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **base,
    )
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth/refresh",  # Scoped: only sent to the refresh endpoint
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Remove both auth cookies from the browser."""
    response.delete_cookie(key=_ACCESS_COOKIE, path="/")
    response.delete_cookie(
        key=_REFRESH_COOKIE,
        path="/api/v1/auth/refresh",
    )


@router.post("/token", response_model=UserResponse)
async def login(
    data: LoginRequest, request: Request, response: Response, db: DbSession
):
    """Authenticate with email and password. Sets HttpOnly auth cookies."""
    ip = get_client_ip(request)
    await login_limiter.check(ip)
    service = AuthService(db)
    user, access_token, refresh_token = await service.login(data.email, data.password)
    _set_auth_cookies(response, access_token, refresh_token)
    await login_limiter.clear(ip)
    return user


@router.post("/refresh", response_model=UserResponse)
async def refresh_token(request: Request, response: Response, db: DbSession):
    """Issue new tokens using the refresh cookie. Returns updated user info."""
    token = request.cookies.get(_REFRESH_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No hay sesión activa. Inicia sesión de nuevo.",
        )
    service = AuthService(db)
    user, access_token, new_refresh_token = await service.refresh(token)
    _set_auth_cookies(response, access_token, new_refresh_token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    """Invalidate the session by clearing auth cookies."""
    _clear_auth_cookies(response)


@router.post("/activate", response_model=UserResponse)
async def activate_invitation(
    data: InvitationActivateRequest, request: Request, response: Response, db: DbSession
):
    """Activate a pending account using an invitation token and set a password."""
    ip = get_client_ip(request)
    await activation_limiter.check(ip)
    service = AuthService(db)
    user, access_token, refresh_token = await service.activate_invitation(data)
    _set_auth_cookies(response, access_token, refresh_token)
    await activation_limiter.clear(ip)
    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: CurrentUser):
    """Return the currently authenticated user."""
    return current_user
