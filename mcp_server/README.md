# ElectroGes MCP Server

Servidor [Model Context Protocol (MCP)](https://modelcontextprotocol.io) para ElectroGes. Permite que modelos de IA (Claude, GPT-4, etc.) interactúen con el sistema de gestión: analizar datos de clientes, crear presupuestos, gestionar obras y registrar cobros — todo a través de lenguaje natural.

---

## Capacidades

### Resources (lectura)

| URI | Descripción |
|-----|-------------|
| `customer://{id}/summary` | Ficha completa del cliente + timeline de actividad |
| `work-orders://active` | Todas las obras en curso (draft + in_progress) |
| `work-order://{id}/details` | Detalle de obra con KPIs |
| `inventory://alerts` | Artículos por debajo del stock mínimo |
| `dashboard://summary` | KPIs del negocio en tiempo real |

### Tools (acciones)

#### Clientes
| Tool | Descripción |
|------|-------------|
| `search_customers` | Buscar por nombre, NIF/CIF o email |
| `get_customer` | Ficha completa de un cliente |
| `get_customer_timeline` | Historial unificado de actividad |
| `create_customer` | Crear nuevo cliente |

#### Visitas Técnicas
| Tool | Descripción |
|------|-------------|
| `list_site_visits` | Listar visitas con filtros |
| `get_site_visit` | Detalle de una visita |
| `create_site_visit` | Programar visita técnica |
| `update_site_visit_status` | Cambiar estado (programada/completada/cancelada) |

#### Presupuestos
| Tool | Descripción |
|------|-------------|
| `list_budgets` | Listar presupuestos con filtros |
| `get_budget` | Detalle de presupuesto con líneas y totales |
| `create_budget` | Crear presupuesto |
| `add_budget_line` | Añadir línea (mano de obra / material / otros) |
| `send_budget` | Marcar como enviado al cliente |
| `accept_budget` | Aceptar y crear obra automáticamente |
| `reject_budget` | Rechazar presupuesto |
| `create_new_budget_version` | Nueva versión para revisiones |

#### Obras
| Tool | Descripción |
|------|-------------|
| `list_work_orders` | Listar obras con filtros |
| `get_work_order` | Detalle completo con tareas |
| `get_work_order_kpis` | KPIs de rentabilidad y progreso |
| `update_work_order_status` | Cambiar estado de la obra |
| `add_task` | Añadir tarea a una obra |
| `update_task_status` | Actualizar estado de tarea |
| `consume_material` | Registrar consumo real de material |

#### Facturación
| Tool | Descripción |
|------|-------------|
| `list_invoices` | Listar facturas con filtros |
| `get_invoice` | Detalle de factura con cobros |
| `create_invoice_from_work_order` | Crear factura desde una obra |
| `send_invoice` | Marcar como enviada al cliente |
| `register_payment` | Registrar cobro (total o parcial) |
| `get_overdue_invoices` | Listar facturas vencidas |

#### Inventario
| Tool | Descripción |
|------|-------------|
| `list_inventory` | Listar artículos |
| `get_inventory_alerts` | Artículos bajo stock mínimo |
| `get_inventory_item` | Detalle con movimientos de stock |

### Prompts (plantillas de análisis)

| Prompt | Descripción |
|--------|-------------|
| `analyze_customer` | Análisis comercial completo de un cliente |
| `suggest_budget_from_visit` | Propuesta de líneas de presupuesto desde visita técnica |
| `work_order_progress_report` | Informe de estado y rentabilidad de una obra |
| `invoice_collection_strategy` | Plan de acción de cobros para facturas vencidas |

---

## Instalación

### Requisitos

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) como gestor de dependencias
- ElectroGes backend en ejecución y accesible

### Pasos

```bash
cd mcp_server

# Instalar dependencias
uv sync

# Configurar variables de entorno
cp .env.example .env
# Editar .env con la URL del backend y credenciales
```

---

## Configuración

Copia `.env.example` a `.env` y edita:

```bash
# URL del backend de ElectroGes
ELECTROGES_API_URL=http://localhost:8000

# Credenciales (usuario de servicio recomendado)
ELECTROGES_EMAIL=mcp@electroges.dev
ELECTROGES_PASSWORD=tu_password_seguro

# Modo de transporte
MCP_TRANSPORT=stdio   # local con Claude Desktop / Claude Code
# MCP_TRANSPORT=sse   # Docker / red

# Solo para modo SSE
MCP_PORT=8080
```

**Recomendación de seguridad**: crea un usuario dedicado en ElectroGes para el MCP server en lugar de usar el superadmin. Así puedes revocar el acceso sin afectar otras cuentas.

---

## Modos de uso

### Modo stdio — Claude Desktop

Añade en `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "electroges": {
      "command": "uv",
      "args": ["run", "python", "main.py"],
      "cwd": "/ruta/a/electroges/mcp_server",
      "env": {
        "ELECTROGES_API_URL": "http://localhost:8000",
        "ELECTROGES_EMAIL": "admin@electroges.dev",
        "ELECTROGES_PASSWORD": "tu_password"
      }
    }
  }
}
```

### Modo stdio — Claude Code (CLI)

```bash
# Añadir al proyecto
claude mcp add electroges -- uv run python main.py
```

O configurar en `.claude/settings.json`:

```json
{
  "mcpServers": {
    "electroges": {
      "command": "uv",
      "args": ["run", "python", "main.py"],
      "cwd": "mcp_server"
    }
  }
}
```

### Modo SSE — Docker Compose

El servicio `mcp_server` usa el profile `mcp` para no arrancar por defecto:

```bash
# Arrancar solo el backend + MCP server
docker compose --profile mcp up backend mcp_server

# O arrancar todo
docker compose --profile mcp up
```

Variables de entorno para Docker (en `.env` raíz):

```bash
MCP_EMAIL=admin@electroges.dev
MCP_PASSWORD=tu_password_seguro
```

El MCP server estará disponible en `http://localhost:8080/sse`.

---

## Ejemplos de uso

Una vez conectado el MCP server a Claude, puedes hacer preguntas como:

```
"Analiza el historial completo del cliente Juan García"
→ usa el prompt analyze_customer

"¿Qué obras llevan más de 30 días sin cerrarse?"
→ list_work_orders con status='in_progress' + análisis de fechas

"Crea un presupuesto para la instalación eléctrica del local de María López
 basándote en las notas de la visita técnica del martes"
→ get_site_visit + create_budget + add_budget_line × N

"¿Qué facturas están vencidas? Dame un plan de cobros"
→ prompt invoice_collection_strategy

"Registra el cobro de 1.200€ por transferencia en la factura FAC-2025-0042"
→ list_invoices (para encontrar el ID) + register_payment
```

---

## Estructura del proyecto

```
mcp_server/
├── main.py                       # Entry point
├── pyproject.toml
├── .env.example
├── Dockerfile
└── electroges_mcp/
    ├── config.py                 # Pydantic-settings
    ├── client.py                 # HTTP client con auth por cookies
    ├── server.py                 # FastMCP server setup
    ├── resources/                # Lecturas de datos (URIs)
    │   ├── customers.py
    │   ├── work_orders.py
    │   ├── inventory.py
    │   └── dashboard.py
    ├── tools/                    # Acciones ejecutables
    │   ├── customers.py
    │   ├── site_visits.py
    │   ├── budgets.py
    │   ├── work_orders.py
    │   ├── invoicing.py
    │   └── inventory.py
    └── prompts/                  # Plantillas de análisis guiado
        └── templates.py
```

---

## Flujo de autenticación

El servidor MCP se autentica contra el backend de ElectroGes usando email y contraseña. El backend establece cookies JWT HttpOnly (`access_token` + `refresh_token`). El cliente httpx gestiona automáticamente el cookie jar — no se expone el token en ningún momento.

Si una petición recibe un 401, el cliente vuelve a hacer login automáticamente y reintenta la petición una vez.
