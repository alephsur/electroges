from decimal import Decimal

from pydantic import BaseModel, EmailStr


class CompanySettingsUpdate(BaseModel):
    company_name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    phone: str | None = None
    email: str | None = None
    bank_account: str | None = None
    general_conditions: str | None = None
    default_tax_rate: Decimal | None = None
    default_validity_days: int | None = None


class CompanySettingsResponse(BaseModel):
    company_name: str
    tax_id: str | None
    address: str | None
    city: str | None
    postal_code: str | None
    phone: str | None
    email: str | None
    bank_account: str | None
    logo_path: str | None
    general_conditions: str | None
    default_tax_rate: float
    default_validity_days: int

    model_config = {"from_attributes": True}
