from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "ElectroGes"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str

    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    # Uploads
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Email / SMTP
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@electroges.local"
    # STARTTLS — upgrades a plain connection to TLS (port 587, most providers)
    SMTP_USE_TLS: bool = True
    # Direct SSL — full SSL from the start (port 465); mutually exclusive with SMTP_USE_TLS
    SMTP_USE_SSL: bool = False

    # Auth cookies
    # Set COOKIE_SECURE=true in production (requires HTTPS).
    # In development the Vite proxy makes requests same-origin, so False is safe.
    COOKIE_SECURE: bool = False
    # "lax" is correct when frontend and backend share the same origin via a proxy.
    # Use "strict" in production for maximum protection.
    COOKIE_SAMESITE: str = "lax"

    # Multi-tenancy bootstrap
    SUPERADMIN_EMAIL: str = "admin@electroges.dev"
    # Frontend URL used for invitation links
    FRONTEND_URL: str = "http://localhost:5173"
    # Invitation token TTL in hours
    INVITATION_EXPIRE_HOURS: int = 48


settings = Settings()
