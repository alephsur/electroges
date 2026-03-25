from fastapi import APIRouter

from app.api.v1.routers import auth

# Phase 1 modules — registered as each module is implemented
# from app.api.v1.routers import customers, site_visits, budgets
# from app.api.v1.routers import work_orders, invoicing, inventory, suppliers

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)

# api_router.include_router(customers.router)
# api_router.include_router(site_visits.router)
# api_router.include_router(budgets.router)
# api_router.include_router(work_orders.router)
# api_router.include_router(invoicing.router)
# api_router.include_router(inventory.router)
# api_router.include_router(suppliers.router)
