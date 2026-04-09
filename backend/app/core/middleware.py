"""Custom Starlette middleware for HTTP security headers.

Headers applied to every response
──────────────────────────────────
X-Content-Type-Options       Prevent MIME-type sniffing.
X-Frame-Options              Block the app from being embedded in iframes.
X-XSS-Protection             Explicitly disabled (value "0") — modern browsers
                             handle XSS natively; the old filter can introduce
                             new vulnerabilities.
Referrer-Policy              Limit referrer leakage to origin-only on
                             cross-origin requests.
Permissions-Policy           Deny access to device APIs not used by the app.
Content-Security-Policy      See note below.

Strict-Transport-Security    Only added when COOKIE_SECURE=true (production),
                             since HSTS is meaningless over plain HTTP.

CSP strategy
────────────
The backend serves two distinct surfaces:
  • /api/**            — JSON responses. CSP has no effect on JSON, but
                         "frame-ancestors 'none'" still protects any HTML
                         error pages FastAPI may render.
  • /docs, /redoc,     — Swagger / ReDoc developer UIs. These load inline
    /openapi.json        scripts, CDN assets and data: URIs, so a blanket
                         'none' policy would break them. A permissive CSP
                         is acceptable because these endpoints are internal
                         developer tooling and can be disabled in production
                         via FastAPI(docs_url=None).
  • /uploads/**        — Static files (images, PDFs). The 'none' CSP is
                         fine: PDFs render in a sandboxed viewer and images
                         are served as binary, not as HTML.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

# Paths that serve developer UIs requiring a relaxed CSP.
_DOC_PREFIXES = ("/docs", "/redoc", "/openapi.json")

# CSP for every endpoint except the developer UIs.
_CSP_STRICT = (
    "default-src 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'none'"
)

# CSP for Swagger / ReDoc — permissive enough for CDN assets and inline scripts.
_CSP_DOCS = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net unpkg.com; "
    "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
    "font-src 'self' fonts.gstatic.com data:; "
    "img-src 'self' data: https:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security-related HTTP response headers on every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # ── Headers applied unconditionally ──────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), "
            "usb=(), bluetooth=(), serial=()"
        )

        # ── HSTS — only meaningful over HTTPS (production) ───────────────────
        if settings.COOKIE_SECURE:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # ── Content-Security-Policy ──────────────────────────────────────────
        is_doc_path = any(request.url.path.startswith(p) for p in _DOC_PREFIXES)
        response.headers["Content-Security-Policy"] = (
            _CSP_DOCS if is_doc_path else _CSP_STRICT
        )

        return response
