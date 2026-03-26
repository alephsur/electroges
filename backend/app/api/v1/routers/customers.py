import uuid

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.customer import (
    CustomerAddressCreate,
    CustomerAddressResponse,
    CustomerAddressUpdate,
    CustomerCreate,
    CustomerDocumentResponse,
    CustomerListResponse,
    CustomerResponse,
    CustomerTimeline,
    CustomerUpdate,
)
from app.services.customer import CustomerService

router = APIRouter(prefix="/customers", tags=["Clientes"])


# ── Customers ─────────────────────────────────────────────────────────────────

@router.get("", response_model=CustomerListResponse)
async def list_customers(
    db: DbSession,
    _: CurrentUser,
    q: str | None = Query(default=None, description="Search by name, tax ID, email or contact"),
    customer_type: str | None = Query(default=None),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
):
    """Return a paginated list of customers with optional filters."""
    return await CustomerService(db).list_customers(
        q=q,
        customer_type=customer_type,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(data: CustomerCreate, db: DbSession, _: CurrentUser):
    """Create a new customer, optionally with an initial address."""
    return await CustomerService(db).create_customer(data)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: uuid.UUID, db: DbSession, _: CurrentUser):
    """Return a single customer with addresses and documents."""
    return await CustomerService(db).get_customer(customer_id)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: uuid.UUID, data: CustomerUpdate, db: DbSession, _: CurrentUser
):
    """Partially update a customer."""
    return await CustomerService(db).update_customer(customer_id, data)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_customer(customer_id: uuid.UUID, db: DbSession, _: CurrentUser):
    """Soft-delete a customer (sets is_active = False)."""
    await CustomerService(db).deactivate_customer(customer_id)


# ── Timeline ──────────────────────────────────────────────────────────────────

@router.get("/{customer_id}/timeline", response_model=CustomerTimeline)
async def get_customer_timeline(customer_id: uuid.UUID, db: DbSession, _: CurrentUser):
    """Return the unified activity timeline for a customer (lazy-loaded by the frontend)."""
    return await CustomerService(db).get_timeline(customer_id)


# ── Addresses ─────────────────────────────────────────────────────────────────

@router.get("/{customer_id}/addresses", response_model=list[CustomerAddressResponse])
async def list_addresses(customer_id: uuid.UUID, db: DbSession, _: CurrentUser):
    """Return all addresses for a customer."""
    return await CustomerService(db).list_addresses(customer_id)


@router.post(
    "/{customer_id}/addresses",
    response_model=CustomerAddressResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_address(
    customer_id: uuid.UUID, data: CustomerAddressCreate, db: DbSession, _: CurrentUser
):
    """Add a new address to a customer."""
    return await CustomerService(db).add_address(customer_id, data)


@router.patch(
    "/{customer_id}/addresses/{address_id}", response_model=CustomerAddressResponse
)
async def update_address(
    customer_id: uuid.UUID,
    address_id: uuid.UUID,
    data: CustomerAddressUpdate,
    db: DbSession,
    _: CurrentUser,
):
    """Partially update a customer address."""
    return await CustomerService(db).update_address(customer_id, address_id, data)


@router.delete(
    "/{customer_id}/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_address(
    customer_id: uuid.UUID, address_id: uuid.UUID, db: DbSession, _: CurrentUser
):
    """Delete an address. The last address cannot be deleted."""
    await CustomerService(db).delete_address(customer_id, address_id)


@router.post(
    "/{customer_id}/addresses/{address_id}/set-default",
    response_model=CustomerAddressResponse,
)
async def set_default_address(
    customer_id: uuid.UUID, address_id: uuid.UUID, db: DbSession, _: CurrentUser
):
    """Mark an address as the default for the customer."""
    return await CustomerService(db).set_default_address(customer_id, address_id)


# ── Documents ─────────────────────────────────────────────────────────────────

@router.get("/{customer_id}/documents", response_model=list[CustomerDocumentResponse])
async def list_documents(customer_id: uuid.UUID, db: DbSession, _: CurrentUser):
    """Return all documents for a customer."""
    return await CustomerService(db).list_documents(customer_id)


@router.post(
    "/{customer_id}/documents",
    response_model=CustomerDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    customer_id: uuid.UUID,
    db: DbSession,
    _: CurrentUser,
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
    name: str | None = Form(default=None),
):
    """Upload a document and attach it to a customer (multipart/form-data)."""
    return await CustomerService(db).upload_document(customer_id, file, document_type, name)


@router.delete(
    "/{customer_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_document(
    customer_id: uuid.UUID, document_id: uuid.UUID, db: DbSession, _: CurrentUser
):
    """Delete a document and its associated file from disk."""
    await CustomerService(db).delete_document(customer_id, document_id)
