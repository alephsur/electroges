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

### Cómo funciona el enrutamiento frontend → backend

El frontend necesita llegar al backend de dos formas distintas según el entorno, lo que da lugar a tres variables relacionadas:

| Variable | Quién la usa | Para qué |
|---|---|---|
| `VITE_API_URL` | El **navegador** (bundle JS compilado) | `baseURL` de axios. En producción se compila vacía para usar rutas relativas vía nginx. En local apunta a `http://localhost:8000`. |
| `BACKEND_INTERNAL_URL` | El **proxy de Vite** en local (proceso Node dentro del contenedor) | Dirige `/api/` y `/uploads/` al backend por la red interna de Docker (`http://backend:8000`). El navegador nunca ve esta variable. |
| `BACKEND_URL` | **nginx** en producción | Inyectada en la config de nginx al arrancar el contenedor. Nginx redirige `/api/`, `/uploads/` y `/health` a este valor. No existe en local. |

**Por qué son necesarias tres variables:**

- `VITE_*` se incrustan en el bundle en tiempo de compilación — el navegador descarga ese valor. En producción se dejan vacías para que axios use rutas relativas (`/api/...`) y nginx las intercepte.
- En local con Docker, el proxy de Vite corre dentro del contenedor frontend. `localhost:8000` apuntaría al propio contenedor, no al backend. Por eso necesita `http://backend:8000` (nombre de servicio de Docker Compose).
- En producción, nginx (no Vite) hace el proxy. `BACKEND_URL` le dice a nginx la URL real del backend.

### Variables para entorno local (archivo `.env`)

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

# Frontend — URL del backend vista desde el navegador
# El proxy de Vite intercepta /api/ y /uploads/ y los redirige internamente,
# por lo que este valor solo se usa si el frontend se ejecuta fuera de Docker.
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

> `BACKEND_INTERNAL_URL` no va en `.env` — está hardcodeada en `docker-compose.yml` como `http://backend:8000` (red interna de Docker).

### Variables para producción (cualquier cloud)

Configurar en el panel de la plataforma — **no en `.env`**:

```bash
# Base de datos
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Seguridad
SECRET_KEY=clave_aleatoria_larga_y_segura

# Entorno
ENVIRONMENT=production
ALLOWED_ORIGINS=["https://tu-dominio.com"]

# Frontend: URL interna del backend (usada por nginx)
# El bundle JS se compila con VITE_API_URL="" para usar rutas relativas.
BACKEND_URL=https://tu-backend.app

# Email — SMTP
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_cuenta@gmail.com
SMTP_PASSWORD=tu_app_password
SMTP_FROM_EMAIL=ElectroGes <tu_cuenta@gmail.com>
SMTP_USE_TLS=true

# Multi-tenant
FRONTEND_URL=https://tu-dominio.com
SUPERADMIN_EMAIL=admin@tu-empresa.com
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
