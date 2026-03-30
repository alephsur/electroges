from fastapi import APIRouter

from app.api.v1.routers import auth, budgets, customers, inventory, site_visits, suppliers

# Phase 1 modules — to be registered as each module is implemented
# from app.api.v1.routers import work_orders, invoicing

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(suppliers.router)
api_router.include_router(inventory.router)
api_router.include_router(customers.router)
api_router.include_router(site_visits.router)
api_router.include_router(budgets.router)

# api_router.include_router(work_orders.router)
# api_router.include_router(invoicing.router)
