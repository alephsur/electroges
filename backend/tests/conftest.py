"""
Root conftest: sets required env vars before any app module is imported,
then eagerly imports all SQLAlchemy models so the mapper registry is fully
configured before any test instantiates a model.

Without this, instantiating e.g. Customer() triggers mapper configuration
and SQLAlchemy raises InvalidRequestError because related models (Tenant,
User, …) haven't been imported yet.
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test_db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only-not-for-production")

# Must come AFTER env vars are set (models import settings transitively).
import app.models  # noqa: E402, F401 — registers all mappers
