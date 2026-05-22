import anyio
from starlette.types import ASGIApp, Receive, Scope, Send

from electroges_mcp.client import ElectroGesClient
from electroges_mcp.config import settings
from electroges_mcp.server import create_server

client = ElectroGesClient(
    base_url=settings.electroges_api_url,
    email=settings.electroges_email,
    password=settings.electroges_password,
)

mcp = create_server(client, host=settings.mcp_host, port=settings.mcp_port)


class _AcceptHeaderNormalizer:
    """ASGI middleware: ensures incoming HTTP requests advertise both
    application/json and text/event-stream in their Accept header.

    FastMCP's streamable-http transport rejects (406) requests that don't
    list both. Some MCP clients (e.g. Hermes Agent) only send
    application/json, which is technically valid HTTP but trips FastMCP.
    This wrapper rewrites the header before the request reaches FastMCP.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = list(scope.get("headers", []))
            rewritten: list[tuple[bytes, bytes]] = []
            saw_accept = False
            for name, value in headers:
                if name == b"accept":
                    saw_accept = True
                    parts = {p.strip().split(b";")[0] for p in value.split(b",")}
                    extras: list[bytes] = []
                    if b"application/json" not in parts:
                        extras.append(b"application/json")
                    if b"text/event-stream" not in parts:
                        extras.append(b"text/event-stream")
                    if extras:
                        value = value + b", " + b", ".join(extras)
                rewritten.append((name, value))
            if not saw_accept:
                rewritten.append((b"accept", b"application/json, text/event-stream"))
            scope = {**scope, "headers": rewritten}
        await self._app(scope, receive, send)


class _BearerAuthWrapper:
    """ASGI middleware: rejects requests without a valid Bearer token.

    Wraps the FastMCP Starlette app so every HTTP request (SSE handshake
    and message POSTs) must carry 'Authorization: Bearer <token>'.
    Disabled when mcp_bearer_token is empty (stdio / local dev).
    """

    _UNAUTHORIZED = (
        b'{"error":"unauthorized","message":"Bearer token required"}'
    )

    def __init__(self, app: ASGIApp, token: str) -> None:
        self._app = app
        self._expected = f"Bearer {token}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            if headers.get(b"authorization") != self._expected:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"www-authenticate", b'Bearer realm="electroges-mcp"'),
                            (b"content-length", str(len(self._UNAUTHORIZED)).encode()),
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": self._UNAUTHORIZED,
                        "more_body": False,
                    }
                )
                return
        await self._app(scope, receive, send)


def main() -> None:
    match settings.mcp_transport:
        case "streamable-http":
            anyio.run(_run_http)
        case "sse":
            anyio.run(_run_sse)
        case _:
            mcp.run()


async def _run_http() -> None:
    """Streamable HTTP transport — POST to /mcp. Default for remote deployments."""
    import uvicorn

    app: ASGIApp = mcp.streamable_http_app()
    app = _AcceptHeaderNormalizer(app)

    if settings.mcp_bearer_token:
        app = _BearerAuthWrapper(app, settings.mcp_bearer_token)

    config = uvicorn.Config(
        app,
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level="info",
    )
    await uvicorn.Server(config).serve()


async def _run_sse() -> None:
    """Legacy SSE transport — GET to /sse. Use transport: sse in Hermes config."""
    import uvicorn

    app: ASGIApp = mcp.sse_app()
    app = _AcceptHeaderNormalizer(app)

    if settings.mcp_bearer_token:
        app = _BearerAuthWrapper(app, settings.mcp_bearer_token)

    config = uvicorn.Config(
        app,
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level="info",
    )
    await uvicorn.Server(config).serve()


if __name__ == "__main__":
    main()
