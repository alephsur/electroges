from electroges_mcp.client import ElectroGesClient
from electroges_mcp.config import settings
from electroges_mcp.server import create_server

client = ElectroGesClient(
    base_url=settings.electroges_api_url,
    email=settings.electroges_email,
    password=settings.electroges_password,
)

mcp = create_server(client)


def main() -> None:
    if settings.mcp_transport == "sse":
        mcp.run(transport="sse", host=settings.mcp_host, port=settings.mcp_port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
