"""In-memory sliding-window rate limiter for login endpoints.

Designed for single-process deployments (Docker Compose, one backend container).
If the app ever scales to multiple processes, replace with a Redis-backed
implementation (e.g. slowapi + redis).
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """Sliding-window counter keyed by an arbitrary string (e.g. client IP)."""

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> None:
        """
        Record one attempt for *key*.
        Raises HTTP 429 with Retry-After if the limit is exceeded.
        """
        async with self._lock:
            now = time.monotonic()
            window_start = now - self.window_seconds
            bucket = self._attempts[key]

            # Evict timestamps outside the current window
            while bucket and bucket[0] < window_start:
                bucket.popleft()

            if len(bucket) >= self.max_attempts:
                retry_after = int(bucket[0] + self.window_seconds - now) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Demasiados intentos. Vuelve a intentarlo en "
                        f"{retry_after // 60} min {retry_after % 60} s."
                    ),
                    headers={"Retry-After": str(retry_after)},
                )

            bucket.append(now)

    async def clear(self, key: str) -> None:
        """Remove all recorded attempts for *key* (call after a successful login)."""
        async with self._lock:
            self._attempts.pop(key, None)


# Shared instances — module-level singletons, created once at import time.
# 5 failed attempts per IP within 15 minutes.
login_limiter = SlidingWindowRateLimiter(max_attempts=5, window_seconds=900)

# 10 activation attempts per IP within 1 hour (tokens are single-use,
# but we still want to prevent token enumeration).
activation_limiter = SlidingWindowRateLimiter(max_attempts=10, window_seconds=3600)


def get_client_ip(request: Request) -> str:
    """
    Return the real client IP, respecting X-Forwarded-For when behind a proxy.
    Falls back to the direct connection address.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can be a comma-separated list; the first entry is the client
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
