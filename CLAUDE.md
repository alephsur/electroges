# CLAUDE.md — ElectroGes

## Descripción del proyecto

**ElectroGes** es un sistema de gestión integral para una empresa pequeña de instalaciones eléctricas. Digitaliza y centraliza las operaciones del negocio en una única plataforma web: clientes, visitas técnicas, presupuestos, obras, facturación, inventario, proveedores, calendario y dashboard.

Arquitectura **multi-tenant**: cada empresa opera en su propio tenant aislado. Escala objetivo: equipos de 2–10 personas.

---

## Stack tecnológico obligatorio

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, PostgreSQL 16, SQLAlchemy async 2.0, Alembic, uv (gestor de dependencias), ruff (linter/formatter) |
| Frontend | React 18, Vite, Tailwind CSS, Zustand, TanStack Query v5 |
| Auth | JWT con refresh tokens, RBAC (superadmin / admin / user) |
| PDF | WeasyPrint |
| Email | aiosmtplib (SMTP opcional, fallback a log en consola) |
| Infraestructura | Docker + Docker Compose |

No sugerir alternativas a este stack salvo que haya un bloqueo técnico justificado.

---

## Módulos del sistema

### Fase 1 – MVP (✅ completada)

| # | Módulo | Estado | Notas |
|---|---|---|---|
| 0 | **Auth / Usuarios / Tenants** | ✅ | JWT + refresh, roles, invitaciones por email, bootstrap de superadmin |
| 1 | **Clientes** | ✅ | Ficha, direcciones, documentos adjuntos, timeline de actividad |
| 2 | **Visitas Técnicas** | ✅ | Notas, materiales estimados, fotos, croquis, documentos |
| 3 | **Presupuestos** | ✅ | Líneas tipadas, capítulos (secciones), margen interno, versiones, descuento por línea y global, PDF, plantillas, importación CSV/Excel, conversión a obra |
| 4 | **Obras** | ✅ | Tareas, materiales previstos/consumidos, certificaciones, albaranes, vínculo con pedidos de compra, KPIs |
| 5 | **Facturación** | ✅ | Facturas desde obra/certificación, pagos parciales, rectificativas, PDF, recordatorio de cobro por email |
| 6 | **Inventario** | ✅ | Stock, movimientos entrada/salida, stock mínimo, alertas de reposición |
| 7 | **Proveedores** | ✅ | Ficha, artículos por proveedor, pedidos de compra |
| 8 | **Dashboard** | ✅ | KPIs, gráfico de facturación mensual, cash-flow, rentabilidad por obra, top clientes/deudores, alertas personalizadas, actividad reciente |
| — | **Calendario** | ✅ | Eventos manuales con color, vista de planificación (adelantado desde Fase 2) |
| — | **MCP Server** | ✅ | Servidor Model Context Protocol en `mcp_server/` para operar el sistema desde IA |

### Fase 2 – Gestión de equipo (pendiente)

| # | Módulo | Estado | Notas |
|---|---|---|---|
| 9 | **Operarios** | ⬜ Diferido | FK `assigned_to` preparada en WorkOrder desde Fase 1 |
| 10 | **Partes de trabajo** | ⬜ Diferido | `estimated_hours` / `actual_hours` ya existen en Task |

> **Leyenda:** ⬜ Pendiente · 🔄 En progreso · ✅ Completado

---

## Flujo principal del sistema

```
Cliente
  └─→ Visita Técnica
           │  notas técnicas, fotos, materiales estimados
           └─→ Presupuesto (borrador)
                    │  líneas: labor | material | other, agrupables en capítulos
                    │  margen interno por línea y total (nunca en el PDF del cliente)
                    │  versiones si el cliente pide cambios (parent_budget_id)
                    │  export PDF → envío al cliente
                    ├─→ [rechazado] → cerrado, queda registrado
                    └─→ [aceptado]
                              └─→ Obra (automática)
                                       │  BudgetLine(labor)    → Task
                                       │  BudgetLine(material) → Task + TaskMaterial
                                       ├─→ Tareas + Materiales (consumo ↔ inventario)
                                       ├─→ Certificaciones parciales (opcional)
                                       ├─→ Albaranes de obra
                                       └─→ Factura → Cobro(s) ✓
```

---

## Modelo de datos — Entidades principales

Todas las tablas de negocio llevan `tenant_id`, `created_at` y `updated_at`.

```
Tenant
 └── User (superadmin sin tenant; admin/user por tenant)

Customer
 ├── direcciones, documentos, timeline
 ├── SiteVisit (1..N)
 │    ├── status: scheduled|completed|cancelled
 │    ├── SiteVisitMaterial / SiteVisitPhoto / SiteVisitDocument
 │    └── Budget (1..N)
 │         ├── budget_number (PRES-YYYY-NNNN)
 │         ├── status: draft|sent|accepted|rejected (expired se calcula en runtime)
 │         ├── version, parent_budget_id, is_latest_version
 │         ├── tax_rate, discount_pct (global)
 │         ├── BudgetSection (capítulos, 0..N)
 │         └── BudgetLine (1..N)
 │              ├── line_type: labor | material | other
 │              ├── inventory_item_id → InventoryItem (nullable)
 │              ├── quantity, unit, unit_price (venta), unit_cost (interno)
 │              └── line_discount_pct
 └── WorkOrder (1..N)
      ├── origin_budget_id → Budget (nullable: obras sin presupuesto)
      ├── assigned_to → Operator (nullable, Fase 2)
      ├── status: draft|active|pending_closure|closed|cancelled
      ├── Task (1..N)
      │    ├── status: pending|in_progress|completed
      │    ├── estimated_hours, actual_hours, unit_price
      │    └── TaskMaterial (estimated_quantity, consumed_quantity, unit_cost)
      ├── Certification (1..N) → CertificationItem
      ├── DeliveryNote (1..N) → DeliveryNoteItem
      ├── WorkOrderPurchaseOrder (vínculo N:M con PurchaseOrder)
      └── Invoice (1..N)
           ├── status: draft|sent|paid|cancelled (overdue se deriva de due_date)
           ├── is_rectification, rectifies_invoice_id
           ├── InvoiceLine (origin: certification|task|manual)
           └── Payment (1..N, pagos parciales, payment_method)

BudgetTemplate (plantillas reutilizables de presupuesto)

InventoryItem
 ├── supplier_id → Supplier
 ├── SupplierItem (precios por proveedor)
 └── StockMovement (entry|exit, vinculado a obra)

Supplier
 └── PurchaseOrder (1..N)

CalendarEvent (eventos manuales, color, all_day)
CompanySettings (datos fiscales, logo — por tenant)
```

---

## Reglas de negocio clave

```
stock_available    = stock_current - SUM(estimated_quantity
                     WHERE task.status IN ['pending','in_progress'])

work_order_cost    = SUM(consumed_quantity × unit_cost)
                     FROM task_materials JOIN tasks
                     WHERE work_order_id = ?

Márgenes — SIEMPRE sobre importes sin IVA (el IVA no es ingreso):
  effective_price  = unit_price × (1 - line_discount_pct / 100)
  margin_pct línea = (effective_price - unit_cost) / effective_price
  margen global    = (taxable_base - total_cost) / taxable_base
                     (taxable_base = subtotal - descuento global, antes de IVA)
  → solo visible internamente, nunca en el PDF del cliente
  → semáforo: <15% rojo · 15-25% ámbar · >25% verde

Totales de presupuesto: nunca se persisten, se calculan en runtime
(BudgetService._calculate_totals).

work_order_status  → 'pending_closure'
                     WHEN ALL tasks.status = 'completed'

budget → work_order conversion:
  BudgetLine(labor)    → Task(name, estimated_hours)
  BudgetLine(material) → Task + TaskMaterial(estimated_quantity, unit_cost)
  BudgetLine(other)    → WorkOrder.notes (sin conversión estructural)
```

---

## Arquitectura del código

### Estructura de capas (backend)

```
routers → services → repositories → models
```

Nunca poner lógica de negocio en los routers. Nunca acceder a la base de datos desde los servicios directamente; usar siempre el repositorio.

### Estructura de carpetas (backend)

```
backend/app/
├── api/v1/routers/         # Un archivo por módulo (auth, budgets, budget_templates,
│                           #  calendar, customers, dashboard, inventory, invoicing,
│                           #  site_visits, suppliers, tenants, work_orders)
├── services/               # Lógica de negocio
├── repositories/           # Acceso a datos
├── models/                 # Modelos SQLAlchemy 2.0
├── schemas/                # Schemas Pydantic v2
├── core/                   # Config, seguridad, DB session, email, bootstrap
├── templates/              # Plantillas HTML para PDF (budget, invoice,
│                           #  certification, delivery_note)
└── utils/                  # pdf_renderer, helpers

backend/migrations/         # Migraciones Alembic (0001..0022+)
backend/tests/unit/         # Tests unitarios (servicios y schemas)
```

### Estructura de carpetas (frontend)

```
frontend/src/
├── features/               # admin, auth, budgets, calendar, customers, dashboard,
│                           #  inventory, invoicing, site-visits, suppliers, work-orders
├── shared/
│   ├── components/         # AppLayout, InventoryItemPicker, ui/
│   ├── hooks/
│   └── utils/
└── lib/                    # Clientes HTTP, configuración

mcp_server/                 # Servidor MCP (tools, resources, prompts)
```

---

## Convenciones de nomenclatura

- **Todo el código en inglés**: variables, funciones, clases, métodos, constantes, parámetros, nombres de archivos
- Archivos y carpetas Python: `snake_case`
- Archivos y carpetas frontend: `kebab-case`
- Componentes React: `PascalCase`
- Comentarios y docstrings: siempre en inglés
- Mensajes de error al usuario final: en español
- Logs internos: en inglés
- Comunicación en la conversación: en español
- UI del frontend: en español

### Ejemplos correctos

```python
# ✅ Python
def get_site_visit_by_id(visit_id: UUID) -> SiteVisitResponse: ...
budget_status = BudgetStatus.ACCEPTED
```

```typescript
// ✅ TypeScript / React
const budgetLineList = useBudgetStore()
const convertBudgetToWorkOrder = async (budgetId: string) => { ... }
```

### Ejemplos incorrectos

```python
# ❌
def obtener_visita_por_id(id_visita: UUID): ...
estado_presupuesto = EstadoPresupuesto.ACEPTADO
```

---

## Estándares de código

### Backend

- Modelos SQLAlchemy con sintaxis 2.0: `Mapped[]` y `mapped_column()`
- Schemas con Pydantic v2
- IDs: UUID v4 (nunca enteros autoincrementales)
- Toda tabla lleva `created_at` y `updated_at` con timezone, y `tenant_id` si es de negocio
- Proporcionar siempre la migración Alembic junto con el modelo
- Manejo de errores con HTTPException y códigos semánticos
- Tests unitarios en `backend/tests/unit/` para servicios y schemas nuevos

### Frontend

- Componentes funcionales con hooks únicamente (nada de clases)
- Estado global con Zustand; sin Redux
- Llamadas al servidor con TanStack Query v5
- TypeScript estricto en todo el frontend

---

## Decisiones de arquitectura tomadas

| Decisión | Elección | Razón |
|---|---|---|
| Arquitectura | Monolito modular | Escala 1–10 usuarios, sin necesidad de microservicios |
| Multi-tenant | `tenant_id` en todas las tablas de negocio | Varias empresas en una instalación, aislamiento total |
| IDs | UUID v4 | Evita exposición de secuencias, facilita sincronización futura |
| Estado frontend | Zustand | Suficiente para la escala, sin boilerplate de Redux |
| ORM | SQLAlchemy async 2.0 | Rendimiento async, tipado moderno con `Mapped[]` |
| Migraciones | Alembic | Estándar del ecosistema FastAPI/SQLAlchemy |
| Presupuesto | Módulo separado de Facturación | Presupuestar es vender; facturar es cobrar. Ciclos de vida distintos |
| Visita Técnica | Módulo propio, origen del presupuesto | Digitaliza el trabajo de campo y evita pérdida de información |
| Margen en presupuesto | Solo interno, calculado sin IVA | Nunca expuesto en PDF ni vistas de cliente; el IVA no es ingreso |
| Totales de presupuesto | Calculados en runtime, nunca persistidos | Una sola fuente de verdad (`_calculate_totals`) |
| MCP server | Módulo en el mismo repo | Acoplado a la API; mismo ciclo de vida |

---

## Compatibilidad Fase 1 → Fase 2

Las siguientes decisiones garantizan que la transición sea aditiva:

- `WorkOrder` incluye `assigned_to UUID NULL` (FK a `operators`) desde el inicio
- `Task` incluye `estimated_hours` y `actual_hours` desde el inicio
- No hay lógica que asuma usuario único; el sistema es multi-usuario y multi-tenant desde el arranque
- Las migraciones de Fase 2 solo añaden tablas (`operators`, `work_logs`) y activan la FK ya existente

---

## Restricciones de diseño

- Escala objetivo: 2–10 usuarios concurrentes → no sobrediseñar
- Monolito modular: sin microservicios
- Las migraciones deben ser **aditivas**, nunca destructivas
- Sistema de uso interno: no es un SaaS público

---

## Mejoras candidatas (backlog)

Prioridad alta:
- **VeriFactu** (RD 1007/2023): registro de facturación encadenado, QR en PDF, inmutabilidad de facturas emitidas — obligación legal
- **Aceptación de presupuestos online**: enlace público con token para que el cliente acepte/rechace
- **Scheduler** (APScheduler): recordatorios automáticos de facturas vencidas, presupuestos sin respuesta y stock bajo mínimo

Prioridad media: Fase 2 (operarios + partes de trabajo), documentación técnica del sector (CIE/boletines), contratos de mantenimiento recurrente, PWA para uso en campo, exportación contable trimestral.

Deuda técnica: CI (ruff + pytest + tsc), tests de integración, backups automáticos de PostgreSQL.

---

## Historial de cambios

| Fecha | Cambio |
|---|---|
| 2025-01 | Definición inicial del proyecto y módulos base |
| 2025-01 | Añadido módulo Visitas Técnicas como origen del flujo comercial |
| 2025-01 | Separado Presupuestos de Facturación como módulo propio |
| 2025-01 | Añadidas reglas de conversión presupuesto → obra |
| 2025-01 | Añadido margen interno por línea de presupuesto |
| 2025-01 | Añadido soporte a versiones de presupuesto |
| 2025–2026 | Implementada Fase 1 completa + multi-tenant, calendario, plantillas, certificaciones, albaranes, pedidos de compra y MCP server |
| 2026-07 | Corregido cálculo de márgenes: sobre base imponible (sin IVA) y con precio efectivo tras descuento de línea |
| 2026-07 | Documentación actualizada al estado real del sistema |

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)
