import json

from mcp.server.fastmcp import FastMCP

from ..client import ApiError, ElectroGesClient


def register(mcp: FastMCP, client: ElectroGesClient) -> None:
    @mcp.resource("customer://{customer_id}/summary")
    async def customer_summary(customer_id: str) -> str:
        """Full customer profile: contact data, addresses, and activity timeline."""
        try:
            customer = await client.get(f"/api/v1/customers/{customer_id}")
            timeline = await client.get(
                f"/api/v1/customers/{customer_id}/timeline",
                params={"limit": 20},
            )
            return json.dumps(
                {"customer": customer, "recent_activity": timeline},
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        except ApiError as e:
            return json.dumps({"error": e.detail, "status_code": e.status_code})
