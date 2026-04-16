"""Business logic for the Site Visits module."""

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.site_visit import (
    SiteVisit,
    SiteVisitDocument,
    SiteVisitMaterial,
    SiteVisitPhoto,
    SiteVisitStatus,
)
from app.repositories.customer import CustomerRepository
from app.repositories.customer_address import CustomerAddressRepository
from app.repositories.inventory_item import InventoryItemRepository
from app.repositories.site_visit import (
    SiteVisitDocumentRepository,
    SiteVisitMaterialRepository,
    SiteVisitPhotoRepository,
    SiteVisitRepository,
)
from app.schemas.site_visit import (
    SiteVisitCreate,
    SiteVisitDocumentResponse,
    SiteVisitLinkCustomer,
    SiteVisitListResponse,
    SiteVisitMaterialCreate,
    SiteVisitMaterialResponse,
    SiteVisitMaterialUpdate,
    SiteVisitPhotoResponse,
    SiteVisitPhotoUpdate,
    SiteVisitResponse,
    SiteVisitStatusUpdate,
    SiteVisitSummary,
    SiteVisitUpdate,
)

logger = logging.getLogger(__name__)

_VALID_TRANSITIONS: dict[str, set[str]] = {
    "scheduled":   {"in_progress", "cancelled", "no_show"},
    "in_progress": {"completed", "cancelled"},
    "completed":   set(),
    "cancelled":   set(),
    "no_show":     {"scheduled"},
}

_TERMINAL_STATUSES = {SiteVisitStatus.COMPLETED, SiteVisitStatus.CANCELLED, SiteVisitStatus.NO_SHOW}


class SiteVisitService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self._session = session
        self._tenant_id = tenant_id
        self._repo = SiteVisitRepository(session, tenant_id)
        self._material_repo = SiteVisitMaterialRepository(session, tenant_id)
        self._photo_repo = SiteVisitPhotoRepository(session, tenant_id)
        self._doc_repo = SiteVisitDocumentRepository(session, tenant_id)
        self._customer_repo = CustomerRepository(session, tenant_id)
        self._addr_repo = CustomerAddressRepository(session, tenant_id)
        self._item_repo = InventoryItemRepository(session, tenant_id)

    # ── List / detail ─────────────────────────────────────────────────────────

    async def list_visits(
        self,
        q: str | None = None,
        customer_id: uuid.UUID | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> SiteVisitListResponse:
        visits, total = await self._repo.search(
            query=q,
            customer_id=customer_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )
        summaries = [self._build_summary(v) for v in visits]
        return SiteVisitListResponse(items=summaries, total=total, skip=skip, limit=limit)

    async def get_visit(self, visit_id: uuid.UUID) -> SiteVisitResponse:
        visit = await self._repo.get_with_full_detail(visit_id)
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visita técnica no encontrada",
            )
        from app.repositories.budget import BudgetRepository
        budgets_count = await BudgetRepository(self._session).count_by_visit(visit_id)
        return self._build_response(visit, budgets_count=budgets_count)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create_visit(self, data: SiteVisitCreate) -> SiteVisitResponse:
        if data.customer_id:
            customer = await self._customer_repo.get_by_id(data.customer_id)
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente no encontrado",
                )

        address_text = data.address_text
        if data.customer_address_id:
            address = await self._addr_repo.get_by_id(data.customer_address_id)
            if not address:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dirección no encontrada",
                )
            if data.customer_id and address.customer_id != data.customer_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La dirección seleccionada no pertenece a este cliente",
                )
            # Snapshot the address so future address changes don't affect the visit record
            if not address_text:
                parts = [address.street, address.city, address.postal_code]
                if address.province:
                    parts.append(address.province)
                address_text = ", ".join(parts)

        visit_data = data.model_dump()
        visit_data["address_text"] = address_text
        visit_data["tenant_id"] = self._tenant_id
        visit = SiteVisit(**visit_data)
        visit = await self._repo.create(visit)
        await self._session.commit()
        logger.info("SiteVisit created id=%s", visit.id)
        return await self.get_visit(visit.id)

    async def update_visit(
        self, visit_id: uuid.UUID, data: SiteVisitUpdate
    ) -> SiteVisitResponse:
        visit = await self._repo.get_by_id(visit_id)
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visita técnica no encontrada",
            )
        if visit.status in _TERMINAL_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede modificar una visita en estado '{visit.status.value}'. "
                       "Solo se puede editar el estado.",
            )
        await self._repo.update(visit, data.model_dump(exclude_unset=True))
        await self._session.commit()
        return await self.get_visit(visit_id)

    # ── Status management ─────────────────────────────────────────────────────

    async def update_status(
        self, visit_id: uuid.UUID, data: SiteVisitStatusUpdate
    ) -> SiteVisitResponse:
        visit = await self._repo.get_by_id(visit_id)
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visita técnica no encontrada",
            )
        self._validate_status_transition(visit.status.value, data.status)
        await self._repo.update(visit, {"status": data.status})
        await self._session.commit()
        logger.info("SiteVisit %s status → %s", visit_id, data.status)
        return await self.get_visit(visit_id)

    def _validate_status_transition(self, current: str, new: str) -> None:
        valid = _VALID_TRANSITIONS.get(current, set())
        if new not in valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede cambiar el estado de '{current}' a '{new}'",
            )

    # ── Link customer ─────────────────────────────────────────────────────────

    async def link_customer(
        self, visit_id: uuid.UUID, data: SiteVisitLinkCustomer
    ) -> SiteVisitResponse:
        visit = await self._repo.get_by_id(visit_id)
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visita técnica no encontrada",
            )
        if visit.customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta visita ya tiene un cliente asignado. Edita la visita para cambiarlo.",
            )
        customer = await self._customer_repo.get_by_id(data.customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado",
            )

        update_data: dict = {"customer_id": data.customer_id}
        if data.customer_address_id:
            update_data["customer_address_id"] = data.customer_address_id

        await self._repo.update(visit, update_data)
        await self._session.commit()
        return await self.get_visit(visit_id)

    # ── Materials ─────────────────────────────────────────────────────────────

    async def list_materials(self, visit_id: uuid.UUID) -> list[SiteVisitMaterialResponse]:
        visit = await self._repo.get_with_full_detail(visit_id)
        if not visit:
            raise HTTPException(status_code=404, detail="Visita técnica no encontrada")
        return [self._build_material_response(m) for m in visit.materials]

    async def add_material(
        self, visit_id: uuid.UUID, data: SiteVisitMaterialCreate
    ) -> SiteVisitMaterialResponse:
        visit = await self._repo.get_by_id(visit_id)
        if not visit:
            raise HTTPException(status_code=404, detail="Visita técnica no encontrada")

        unit = data.unit
        unit_cost = data.unit_cost
        item_name = None

        if data.inventory_item_id:
            item = await self._item_repo.get_by_id(data.inventory_item_id)
            if not item:
                raise HTTPException(
                    status_code=404, detail="Material del inventario no encontrado"
                )
            item_name = item.name
            if not unit:
                unit = item.unit
            if not unit_cost:
                unit_cost = item.unit_cost_avg or Decimal("0")

        material_data = data.model_dump()
        material_data["unit"] = unit
        material_data["unit_cost"] = unit_cost

        material = SiteVisitMaterial(site_visit_id=visit_id, **material_data)
        material = await self._material_repo.create(material)
        await self._session.commit()

        return SiteVisitMaterialResponse(
            id=material.id,
            site_visit_id=material.site_visit_id,
            inventory_item_id=material.inventory_item_id,
            inventory_item_name=item_name,
            description=material.description,
            estimated_qty=material.estimated_qty,
            unit=material.unit,
            unit_cost=material.unit_cost,
            subtotal=(
                material.estimated_qty * material.unit_cost if material.unit_cost else None
            ),
            created_at=material.created_at,
        )

    async def update_material(
        self, visit_id: uuid.UUID, material_id: uuid.UUID, data: SiteVisitMaterialUpdate
    ) -> SiteVisitMaterialResponse:
        material = await self._material_repo.get_by_id(material_id)
        if not material or material.site_visit_id != visit_id:
            raise HTTPException(status_code=404, detail="Material no encontrado en esta visita")
        await self._material_repo.update(material, data.model_dump(exclude_unset=True))
        await self._session.commit()
        await self._session.refresh(material)
        return self._build_material_response(material)

    async def delete_material(self, visit_id: uuid.UUID, material_id: uuid.UUID) -> None:
        material = await self._material_repo.get_by_id(material_id)
        if not material or material.site_visit_id != visit_id:
            raise HTTPException(status_code=404, detail="Material no encontrado en esta visita")
        await self._material_repo.delete(material)
        await self._session.commit()

    # ── Photos ────────────────────────────────────────────────────────────────

    async def list_photos(self, visit_id: uuid.UUID) -> list[SiteVisitPhotoResponse]:
        visit = await self._repo.get_by_id(visit_id)
        if not visit:
            raise HTTPException(status_code=404, detail="Visita técnica no encontrada")
        photos = await self._photo_repo.get_by_visit(visit_id)
        return [SiteVisitPhotoResponse.model_validate(p) for p in photos]

    async def upload_photo(
        self, visit_id: uuid.UUID, file: UploadFile, caption: str | None
    ) -> SiteVisitPhotoResponse:
        visit = await self._repo.get_by_id(visit_id)
        if not visit:
            raise HTTPException(status_code=404, detail="Visita técnica no encontrada")

        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se permiten archivos de imagen (JPG, PNG, WEBP)",
            )

        content = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo supera el tamaño máximo de {settings.MAX_UPLOAD_SIZE_MB} MB",
            )

        upload_dir = (
            Path(settings.UPLOAD_DIR) / "site_visits" / str(visit_id) / "photos"
        )
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = upload_dir / safe_filename
        file_path.write_bytes(content)

        current_photos = await self._photo_repo.get_by_visit(visit_id)
        next_order = len(current_photos)

        photo = SiteVisitPhoto(
            site_visit_id=visit_id,
            file_path=str(file_path),
            file_size_bytes=len(content),
            caption=caption,
            sort_order=next_order,
        )
        photo = await self._photo_repo.create(photo)
        await self._session.commit()
        logger.info("Photo uploaded visit_id=%s photo_id=%s", visit_id, photo.id)
        return SiteVisitPhotoResponse.model_validate(photo)

    async def update_photo(
        self, visit_id: uuid.UUID, photo_id: uuid.UUID, data: SiteVisitPhotoUpdate
    ) -> SiteVisitPhotoResponse:
        photo = await self._photo_repo.get_by_id(photo_id)
        if not photo or photo.site_visit_id != visit_id:
            raise HTTPException(status_code=404, detail="Foto no encontrada en esta visita")
        await self._photo_repo.update(photo, data.model_dump(exclude_unset=True))
        await self._session.commit()
        await self._session.refresh(photo)
        return SiteVisitPhotoResponse.model_validate(photo)

    async def delete_photo(self, visit_id: uuid.UUID, photo_id: uuid.UUID) -> None:
        photo = await self._photo_repo.get_by_id(photo_id)
        if not photo or photo.site_visit_id != visit_id:
            raise HTTPException(status_code=404, detail="Foto no encontrada en esta visita")
        file_path = Path(photo.file_path)
        if file_path.exists():
            file_path.unlink()
        await self._photo_repo.delete(photo)
        await self._session.commit()

    async def reorder_photos(
        self, visit_id: uuid.UUID, photo_ids: list[uuid.UUID]
    ) -> list[SiteVisitPhotoResponse]:
        visit = await self._repo.get_by_id(visit_id)
        if not visit:
            raise HTTPException(status_code=404, detail="Visita técnica no encontrada")
        await self._repo.reorder_photos(visit_id, photo_ids)
        await self._session.commit()
        photos = await self._photo_repo.get_by_visit(visit_id)
        return [SiteVisitPhotoResponse.model_validate(p) for p in photos]

    # ── Documents ─────────────────────────────────────────────────────────────

    async def list_documents(self, visit_id: uuid.UUID) -> list[SiteVisitDocumentResponse]:
        visit = await self._repo.get_with_full_detail(visit_id)
        if not visit:
            raise HTTPException(status_code=404, detail="Visita técnica no encontrada")
        return [SiteVisitDocumentResponse.model_validate(d) for d in visit.documents]

    async def upload_document(
        self,
        visit_id: uuid.UUID,
        file: UploadFile,
        document_type: str,
        name: str | None,
    ) -> SiteVisitDocumentResponse:
        visit = await self._repo.get_by_id(visit_id)
        if not visit:
            raise HTTPException(status_code=404, detail="Visita técnica no encontrada")

        content = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo supera el tamaño máximo de {settings.MAX_UPLOAD_SIZE_MB} MB",
            )

        upload_dir = (
            Path(settings.UPLOAD_DIR) / "site_visits" / str(visit_id) / "documents"
        )
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = upload_dir / safe_filename
        file_path.write_bytes(content)

        doc = SiteVisitDocument(
            site_visit_id=visit_id,
            name=name or file.filename or safe_filename,
            file_path=str(file_path),
            file_size_bytes=len(content),
            document_type=document_type,
        )
        doc = await self._doc_repo.create(doc)
        await self._session.commit()
        logger.info("Document uploaded visit_id=%s doc_id=%s", visit_id, doc.id)
        return SiteVisitDocumentResponse.model_validate(doc)

    async def delete_document(self, visit_id: uuid.UUID, doc_id: uuid.UUID) -> None:
        doc = await self._doc_repo.get_by_id(doc_id)
        if not doc or doc.site_visit_id != visit_id:
            raise HTTPException(
                status_code=404, detail="Documento no encontrado en esta visita"
            )
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()
        await self._doc_repo.delete(doc)
        await self._session.commit()

    # ── Private helpers ────────────────────────────────────────────────────────

    def _resolve_address(self, visit: SiteVisit) -> str:
        return visit.address_text or "Sin dirección especificada"

    def _build_summary(self, visit: SiteVisit) -> SiteVisitSummary:
        return SiteVisitSummary(
            id=visit.id,
            customer_id=visit.customer_id,
            customer_name=visit.customer.name if visit.customer else None,
            customer_type=(
                visit.customer.customer_type.value if visit.customer else None
            ),
            address_display=self._resolve_address(visit),
            contact_name=visit.contact_name,
            visit_date=visit.visit_date,
            status=visit.status.value,
            description=visit.description,
            estimated_budget=visit.estimated_budget,
            has_photos=len(visit.photos) > 0,
            has_documents=len(visit.documents) > 0,
            materials_count=len(visit.materials),
            budgets_count=0,
            created_at=visit.created_at,
        )

    def _build_response(self, visit: SiteVisit, budgets_count: int = 0) -> SiteVisitResponse:
        materials = [self._build_material_response(m) for m in visit.materials]
        return SiteVisitResponse(
            id=visit.id,
            customer_id=visit.customer_id,
            customer_name=visit.customer.name if visit.customer else None,
            customer_type=(
                visit.customer.customer_type.value if visit.customer else None
            ),
            customer_address_id=visit.customer_address_id,
            address_text=visit.address_text,
            address_display=self._resolve_address(visit),
            contact_name=visit.contact_name,
            contact_phone=visit.contact_phone,
            visit_date=visit.visit_date,
            estimated_duration_hours=visit.estimated_duration_hours,
            status=visit.status.value,
            description=visit.description,
            work_scope=visit.work_scope,
            technical_notes=visit.technical_notes,
            estimated_hours=visit.estimated_hours,
            estimated_budget=visit.estimated_budget,
            materials=materials,
            photos=[SiteVisitPhotoResponse.model_validate(p) for p in visit.photos],
            documents=[
                SiteVisitDocumentResponse.model_validate(d) for d in visit.documents
            ],
            materials_count=len(materials),
            budgets_count=budgets_count,
            created_at=visit.created_at,
            updated_at=visit.updated_at,
        )

    def _build_material_response(self, m: SiteVisitMaterial) -> SiteVisitMaterialResponse:
        item_name = m.inventory_item.name if m.inventory_item else None
        return SiteVisitMaterialResponse(
            id=m.id,
            site_visit_id=m.site_visit_id,
            inventory_item_id=m.inventory_item_id,
            inventory_item_name=item_name,
            description=m.description,
            estimated_qty=m.estimated_qty,
            unit=m.unit,
            unit_cost=m.unit_cost,
            subtotal=(m.estimated_qty * m.unit_cost if m.unit_cost else None),
            created_at=m.created_at,
        )
