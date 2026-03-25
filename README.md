# ElectroGes

Sistema de gestión integral para empresa de instalaciones eléctricas.

## Stack

- **Backend:** Python 3.12, FastAPI, PostgreSQL 16, SQLAlchemy async 2.0, Alembic
- **Frontend:** React 18, Vite, Tailwind CSS, Zustand, TanStack Query v5
- **Auth:** JWT con refresh tokens
- **Infraestructura:** Docker + Docker Compose

## Arrancar en local

```bash
# 1. Copiar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 2. Levantar todos los servicios
docker compose up --build

# 3. Ejecutar migraciones (primera vez)
docker compose exec backend alembic upgrade head

# 4. Crear primer usuario (primera vez)
docker compose exec backend python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from app.services.auth import AuthService
from app.schemas.auth import UserCreate

async def main():
    async with AsyncSessionLocal() as session:
        svc = AuthService(session)
        await svc.register(UserCreate(
            email='admin@electroges.com',
            full_name='Administrador',
            password='admin1234'
        ))
        print('Usuario creado')

asyncio.run(main())
"
```

## URLs

| Servicio | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

## Desarrollo sin Docker

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Configurar DATABASE_URL en .env
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Estructura del proyecto

```
electroges/
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/   # Endpoints por módulo
│   │   ├── services/         # Lógica de negocio
│   │   ├── repositories/     # Acceso a datos
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   └── core/             # Config, seguridad, DB
│   ├── migrations/           # Alembic
│   └── tests/
└── frontend/
    └── src/
        ├── features/         # Un directorio por módulo
        ├── shared/           # Componentes y hooks reutilizables
        ├── lib/              # Cliente HTTP
        └── types/            # Tipos TypeScript compartidos
```

## Módulos — Estado

| Módulo | Estado |
|---|---|
| Auth / Usuarios | ✅ Scaffolding listo |
| Clientes | ⬜ Pendiente |
| Visitas Técnicas | ⬜ Pendiente |
| Presupuestos | ⬜ Pendiente |
| Obras + Tareas | ⬜ Pendiente |
| Facturación | ⬜ Pendiente |
| Inventario | ⬜ Pendiente |
| Proveedores | ⬜ Pendiente |
| Dashboard | ⬜ Pendiente |
