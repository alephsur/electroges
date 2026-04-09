"""Application startup bootstrap.

On every startup, checks whether a superadmin user exists.
If not, creates one with a randomly generated password and prints it to stdout.
This output is intentionally written to stdout so it survives log filtering in
production environments (e.g. Docker stdout / systemd journal).
"""

import logging
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_secure_password, hash_password
from app.models.user import User, UserRole
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)

_BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║                  ⚠  SUPERADMIN ACCOUNT CREATED  ⚠               ║
╠══════════════════════════════════════════════════════════════════╣
║  Email   : {email:<54}║
║  Password: {password:<54}║
╠══════════════════════════════════════════════════════════════════╣
║  Store this password in a secure place and change it on first   ║
║  login. This message will NOT appear again.                     ║
╚══════════════════════════════════════════════════════════════════╝
"""


async def bootstrap_superadmin(session: AsyncSession) -> None:
    """Create the superadmin user if it does not exist yet."""
    repo = UserRepository(session)

    existing = await repo.get_superadmin()
    if existing:
        logger.info("Superadmin already exists (id=%s). Skipping bootstrap.", existing.id)
        return

    password = generate_secure_password(length=20)
    superadmin = User(
        email=settings.SUPERADMIN_EMAIL,
        full_name="Super Administrador",
        hashed_password=hash_password(password),
        is_active=True,
        role=UserRole.SUPERADMIN,
        tenant_id=None,
    )
    await repo.create(superadmin)
    await session.commit()

    # Write directly to stdout so the password is always visible regardless of
    # log level configuration.
    banner = _BANNER.format(
        email=settings.SUPERADMIN_EMAIL,
        password=password,
    )
    sys.stdout.write(banner)
    sys.stdout.flush()

    logger.info("Superadmin created: email=%s", settings.SUPERADMIN_EMAIL)
