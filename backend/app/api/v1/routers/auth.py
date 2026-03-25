from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.auth import LoginRequest, TokenRefreshRequest, TokenResponse, UserCreate, UserResponse
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


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserCreate, db: DbSession):
    """Register a new user (initial setup only)."""
    service = AuthService(db)
    user = await service.register(data)
    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user_id: CurrentUser, db: DbSession):
    """Return the currently authenticated user."""
    from app.repositories.user import UserRepository
    repo = UserRepository(db)
    user = await repo.get_by_email(current_user_id)
    return user
