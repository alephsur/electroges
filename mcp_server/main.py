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
    if settings.mcp_transport == "sse":
        anyio.run(_run_sse)
    else:
        mcp.run()


async def _run_sse() -> None:
    import uvicorn

    app: ASGIApp = mcp.sse_app()

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
