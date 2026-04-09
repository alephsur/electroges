# ElectroGes

Sistema de gestión integral para empresa de instalaciones eléctricas. Digitaliza y centraliza clientes, visitas técnicas, presupuestos, obras, facturación, inventario y proveedores en una única plataforma web.

Arquitectura multi-tenant preparada para equipos de 2–10 personas.

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI 0.115, PostgreSQL 16, SQLAlchemy async 2.0, Alembic |
| Frontend | React 18, Vite 6, Tailwind CSS 3, Zustand 5, TanStack Query v5 |
| Auth | JWT con refresh tokens, RBAC (superadmin / admin / user) |
| PDF | WeasyPrint |
| Email | aiosmtplib (SMTP opcional) |
| Infraestructura | Docker + Docker Compose |

---

## Arrancar en local

```bash
# 1. Copiar variables de entorno
cp .env.example .env
# Editar .env con los valores de tu entorno (ver sección Variables de entorno)

# 2. Levantar todos los servicios
docker compose up --build

# 3. Ejecutar migraciones (primera vez)
docker compose exec backend alembic upgrade head
```

Al arrancar por primera vez, el backend crea automáticamente el usuario superadmin e imprime sus credenciales en la consola:

```
╔══════════════════════════════════════════════════════════════════╗
║                  ⚠  SUPERADMIN ACCOUNT CREATED  ⚠               ║
╠══════════════════════════════════════════════════════════════════╣
║  Email   : admin@electroges.dev                                  ║
║  Password: <contraseña generada aleatoriamente>                  ║
╚══════════════════════════════════════════════════════════════════╝
```

Con esas credenciales accedes a la UI de administración para crear el primer tenant y sus usuarios.

## URLs

| Servicio | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

---

## Variables de entorno

```bash
# Base de datos
POSTGRES_USER=electroges
POSTGRES_PASSWORD=tu_password_seguro
POSTGRES_DB=electroges

# Seguridad
SECRET_KEY=cambia_esto_en_produccion

# Entorno
ENVIRONMENT=development
ALLOWED_ORIGINS=["http://localhost:5173"]

# Frontend
VITE_API_URL=http://localhost:8000

# Email — SMTP (opcional)
SMTP_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_cuenta@gmail.com
SMTP_PASSWORD=tu_app_password
SMTP_FROM_EMAIL=ElectroGes <tu_cuenta@gmail.com>
SMTP_USE_TLS=true
```

---

## Desarrollo sin Docker

### Backend

```bash
cd backend
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Configurar DATABASE_URL en .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Módulos — Estado

### Fase 1 — MVP

| Módulo | Estado | Notas |
|---|---|---|
| Auth / Usuarios | ✅ Completado | JWT + refresh tokens, roles, invitaciones |
| Multi-tenant | ✅ Completado | Aislamiento completo por tenant |
| Clientes | ✅ Completado | Ficha, direcciones, documentos, timeline |
| Visitas Técnicas | ✅ Completado | Notas, materiales estimados, fotos, croquis |
| Presupuestos | ✅ Completado | Versiones, margen interno, PDF, conversión a obra |
| Obras + Tareas + Materiales | ✅ Completado | Ciclo completo, control de materiales, albaranes |
| Facturación | ✅ Completado | Pagos parciales, rectificativas, PDF, recordatorio por email |
| Inventario | ✅ Completado | Stock, movimientos, alertas de stock mínimo |
| Proveedores | ✅ Completado | Ficha, artículos, pedidos de compra |
| Dashboard | ✅ Completado | KPIs, gráficos de facturación, alertas, actividad reciente |

### Fase 2 — Gestión de equipo (diferido)

| Módulo | Estado | Notas |
|---|---|---|
| Operarios | ⬜ Diferido | FK preparada en `WorkOrder` desde Fase 1 |
| Partes de trabajo | ⬜ Diferido | |
| Calendario | ⬜ Diferido | |

---

## Flujo principal

```
Cliente
  └─→ Visita Técnica
           └─→ Presupuesto (borrador → enviado → aceptado)
                    └─→ Obra (creada automáticamente)
                             ├── Tareas + Materiales
                             ├── Albarán de obra
                             └── Factura → Cobro ✓
```

---

## Arquitectura

### Capas (backend)

```
routers → services → repositories → models
```

La lógica de negocio vive en `services`. El acceso a datos está encapsulado en `repositories`. Los routers solo gestionan HTTP.

### Estructura de carpetas

```
electroges/
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/   # Un archivo por módulo
│   │   ├── services/         # Lógica de negocio
│   │   ├── repositories/     # Acceso a datos
│   │   ├── models/           # SQLAlchemy 2.0 models
│   │   ├── schemas/          # Pydantic v2 schemas
│   │   ├── core/             # Config, seguridad, DB, bootstrap
│   │   └── utils/
│   ├── migrations/           # 18 migraciones Alembic
│   └── tests/
└── frontend/
    └── src/
        ├── features/         # Un directorio por módulo
        │   ├── auth/
        │   ├── dashboard/
        │   ├── customers/
        │   ├── site-visits/
        │   ├── budgets/
        │   ├── work-orders/
        │   ├── invoicing/
        │   ├── inventory/
        │   ├── suppliers/
        │   └── admin/
        ├── shared/           # Componentes y hooks reutilizables
        ├── lib/              # Cliente HTTP, configuración
        └── types/            # Tipos TypeScript compartidos
```

---

## Multi-tenant

Cada empresa opera en su propio tenant completamente aislado. El superadmin crea tenants y puede invitar usuarios con rol `admin` o `user`. Las invitaciones se envían por email (requiere SMTP configurado) o el token de activación se puede copiar desde los logs del backend.

```
Superadmin
  └─→ Crea Tenant (empresa)
           └─→ Invita usuarios (admin / user)
                    └─→ Usuario activa cuenta con token de invitación
```

---

## Decisiones de arquitectura

| Decisión | Elección | Razón |
|---|---|---|
| Arquitectura | Monolito modular | Escala 1–10 usuarios |
| IDs | UUID v4 | Evita exposición de secuencias |
| Estado frontend | Zustand | Sin boilerplate de Redux |
| ORM | SQLAlchemy async 2.0 | Rendimiento async, tipado moderno |
| Presupuesto ≠ Factura | Módulos separados | Ciclos de vida distintos |
| Margen en presupuesto | Solo visible internamente | Nunca expuesto en PDF de cliente |
