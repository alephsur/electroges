from fastapi import APIRouter

from app.api.v1.routers import auth, budgets, customers, inventory, invoicing, site_visits, suppliers, work_orders

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(suppliers.router)
api_router.include_router(inventory.router)
api_router.include_router(customers.router)
api_router.include_router(site_visits.router)
api_router.include_router(budgets.router)
api_router.include_router(work_orders.router)
api_router.include_router(invoicing.router)
