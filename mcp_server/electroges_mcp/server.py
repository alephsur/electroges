from mcp.server.fastmcp import FastMCP

from .client import ElectroGesClient

_INSTRUCTIONS = """
Servidor MCP de ElectroGes — sistema de gestión para empresa de instalaciones eléctricas.

Capacidades disponibles:
- CLIENTES: buscar, consultar ficha completa y timeline de actividad, crear clientes
- VISITAS TÉCNICAS: listar, crear y actualizar estado de visitas previas a obra
- PRESUPUESTOS: listar, crear, añadir líneas (mano de obra / material / otros), enviar, aceptar o rechazar
- OBRAS: listar, consultar KPIs, cambiar estado, añadir tareas y actualizar su estado
- FACTURACIÓN: listar, crear desde obra, registrar cobros, enviar al cliente
- INVENTARIO: consultar stock, alertas de mínimos y detalle de artículos
- DASHBOARD: métricas clave del negocio en tiempo real

Flujo principal:
  Cliente → Visita Técnica → Presupuesto → Obra → Factura → Cobro

Cuando el usuario pida analizar un cliente, usa primero get_customer y get_customer_timeline,
luego list_budgets, list_work_orders y list_invoices filtrando por ese customer_id.
"""


def create_server(client: ElectroGesClient, host: str = "0.0.0.0", port: int = 8080) -> FastMCP:
    mcp = FastMCP("ElectroGes", instructions=_INSTRUCTIONS, host=host, port=port)

    from .resources import customers as customer_resources
    from .resources import dashboard, inventory as inventory_resources
    from .resources import work_orders as wo_resources
    from .tools import budgets, customers as customer_tools
    from .tools import inventory as inventory_tools
    from .tools import invoicing, site_visits
    from .tools import work_orders as wo_tools
    from .prompts import templates

    customer_resources.register(mcp, client)
    wo_resources.register(mcp, client)
    inventory_resources.register(mcp, client)
    dashboard.register(mcp, client)

    customer_tools.register(mcp, client)
    site_visits.register(mcp, client)
    budgets.register(mcp, client)
    wo_tools.register(mcp, client)
    invoicing.register(mcp, client)
    inventory_tools.register(mcp, client)

    templates.register(mcp)

    return mcp
