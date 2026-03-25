import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier import Supplier
from app.repositories.supplier import SupplierRepository
from app.schemas.supplier import (
    SupplierCreate,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdate,
)

logger = logging.getLogger(__name__)


class SupplierService:
    def __init__(self, session: AsyncSession):
        self._repo = SupplierRepository(session)
        self._session = session

    async def list_suppliers(
        self,
        q: str | None = None,
        is_active: bool | None = True,
        skip: int = 0,
        limit: int = 100,
    ) -> SupplierListResponse:
        logger.info("Listing suppliers [q=%r, is_active=%s, skip=%d, limit=%d]", q, is_active, skip, limit)
        suppliers, total = await self._repo.search(
            query=q, is_active=is_active, skip=skip, limit=limit
        )
        logger.info("Found %d suppliers (total=%d)", len(suppliers), total)
        return SupplierListResponse(
            items=[SupplierResponse.model_validate(s) for s in suppliers],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_supplier(self, supplier_id: uuid.UUID) -> SupplierResponse:
        logger.info("Fetching supplier id=%s", supplier_id)
        supplier = await self._repo.get_by_id(supplier_id)
        if not supplier:
            logger.warning("Supplier not found: id=%s", supplier_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proveedor no encontrado",
            )
        return SupplierResponse.model_validate(supplier)

    async def create_supplier(self, data: SupplierCreate) -> SupplierResponse:
        logger.info("Creating supplier name=%r tax_id=%r", data.name, data.tax_id)
        if data.tax_id:
            await self._assert_tax_id_unique(data.tax_id)
        supplier = Supplier(**data.model_dump())
        created = await self._repo.create(supplier)
        await self._session.commit()
        logger.info("Supplier created id=%s", created.id)
        return SupplierResponse.model_validate(created)

    async def update_supplier(
        self, supplier_id: uuid.UUID, data: SupplierUpdate
    ) -> SupplierResponse:
        logger.info("Updating supplier id=%s fields=%s", supplier_id, list(data.model_fields_set))
        supplier = await self._repo.get_by_id(supplier_id)
        if not supplier:
            logger.warning("Supplier not found for update: id=%s", supplier_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proveedor no encontrado",
            )
        update_data = data.model_dump(exclude_unset=True)
        new_tax_id = update_data.get("tax_id")
        if new_tax_id and new_tax_id != supplier.tax_id:
            await self._assert_tax_id_unique(new_tax_id)
        updated = await self._repo.update(supplier, update_data)
        await self._session.commit()
        logger.info("Supplier updated id=%s", supplier_id)
        return SupplierResponse.model_validate(updated)

    async def deactivate_supplier(self, supplier_id: uuid.UUID) -> None:
        logger.info("Deactivating supplier id=%s", supplier_id)
        supplier = await self._repo.get_by_id(supplier_id)
        if not supplier:
            logger.warning("Supplier not found for deactivation: id=%s", supplier_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proveedor no encontrado",
            )
        await self._repo.update(supplier, {"is_active": False})
        await self._session.commit()
        logger.info("Supplier deactivated id=%s", supplier_id)

    # ------------------------------------------------------------------ helpers

    async def _assert_tax_id_unique(self, tax_id: str) -> None:
        existing = await self._repo.get_by_tax_id(tax_id)
        if existing:
            logger.warning("Duplicate tax_id rejected: %r (existing id=%s)", tax_id, existing.id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un proveedor con el CIF/NIF '{tax_id}'",
            )
