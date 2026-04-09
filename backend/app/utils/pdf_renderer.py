"""PDF rendering utilities using Jinja2 + WeasyPrint."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.core.config import settings


def _resolve_company_identity(company) -> tuple[str, str | None]:
    """
    Returns (effective_name, effective_logo_abs_path) for PDF rendering.

    Priority:
    - Name: tenant.name is always the source of truth. company_name from
      CompanySettings is used as an override only when it is explicitly set
      AND different from tenant.name (to avoid stale migration defaults).
    - Logo: company.logo_path if set, else derive absolute path from tenant.logo_url
    """
    tenant_name = (company.tenant.name or "").strip() if company.tenant else ""
    company_name = (company.company_name or "").strip()

    # Use company_name only if explicitly set and different from the tenant name
    # (guards against migration artifacts like "Default Tenant")
    if company_name and company_name != tenant_name:
        name = company_name
    else:
        name = tenant_name

    logo_abs_path: str | None = None
    if company.logo_path:
        logo_abs_path = str(Path(company.logo_path).resolve())
    elif company.tenant and company.tenant.logo_url:
        # tenant.logo_url is a web path like /uploads/logos/{id}/logo.png
        # Strip the leading /uploads prefix and resolve against UPLOAD_DIR
        rel = company.tenant.logo_url.lstrip("/")
        # rel is now "uploads/logos/..."
        candidate = Path(settings.UPLOAD_DIR).parent / rel
        if not candidate.exists():
            # Try relative to current working directory
            candidate = Path(rel)
        if candidate.exists():
            logo_abs_path = str(candidate.resolve())

    return name, logo_abs_path


def _currency_filter(value) -> str:
    """Format a numeric value as euros: 1.234,56 €"""
    try:
        formatted = f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} €"
    except (TypeError, ValueError):
        return "0,00 €"


def _number_filter(value) -> str:
    """Format a number removing trailing zeros."""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return "0"


def _date_filter(value) -> str:
    """Format a date as dd/mm/yyyy."""
    try:
        return value.strftime("%d/%m/%Y")
    except AttributeError:
        return str(value)


def _get_jinja_env() -> Environment:
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
    env.filters["currency"] = _currency_filter
    env.filters["number"] = _number_filter
    env.filters["date"] = _date_filter
    return env


def render_delivery_note_pdf_html(note, work_order, company, customer, totals: dict) -> str:
    """Renders the delivery note PDF HTML using the Jinja2 template."""
    env = _get_jinja_env()
    template = env.get_template("delivery_note_pdf.html")
    effective_name, logo_abs_path = _resolve_company_identity(company)
    return template.render(
        note=note,
        work_order=work_order,
        company=company,
        effective_company_name=effective_name,
        customer=customer,
        totals=totals,
        logo_abs_path=logo_abs_path,
    )


def render_certification_pdf_html(cert, work_order, company, customer, total_amount) -> str:
    """Renders the certification PDF HTML using the Jinja2 template."""
    env = _get_jinja_env()
    template = env.get_template("certification_pdf.html")
    effective_name, logo_abs_path = _resolve_company_identity(company)
    return template.render(
        cert=cert,
        work_order=work_order,
        company=company,
        effective_company_name=effective_name,
        customer=customer,
        total_amount=total_amount,
        logo_abs_path=logo_abs_path,
    )


def render_invoice_pdf_html(invoice, company, totals) -> str:
    """
    Renders the invoice PDF HTML using the Jinja2 template.

    IMPORTANT: `totals` must be an InvoiceTotals instance.
    Internal cost or margin data must NOT be included.
    """
    env = _get_jinja_env()
    template = env.get_template("invoice_pdf.html")
    effective_name, logo_abs_path = _resolve_company_identity(company)

    has_line_discounts = any(
        float(line.line_discount_pct) > 0 for line in (invoice.lines or [])
    )

    return template.render(
        invoice=invoice,
        company=company,
        effective_company_name=effective_name,
        customer=invoice.customer,
        totals=totals,
        lines=invoice.lines or [],
        has_line_discounts=has_line_discounts,
        logo_abs_path=logo_abs_path,
    )


def render_budget_pdf_html(budget, company, totals, customer, address, lines) -> str:
    """
    Renders the budget PDF HTML using the Jinja2 template.

    IMPORTANT: `lines` must be BudgetLinePublicResponse instances —
    they must NOT contain unit_cost or margin fields.
    """
    env = _get_jinja_env()
    template = env.get_template("budget_pdf.html")
    effective_name, logo_abs_path = _resolve_company_identity(company)

    has_line_discounts = any(float(line.line_discount_pct) > 0 for line in lines)

    return template.render(
        budget=budget,
        company=company,
        effective_company_name=effective_name,
        totals=totals,
        customer=customer,
        address=address,
        lines=lines,
        has_line_discounts=has_line_discounts,
        logo_abs_path=logo_abs_path,
    )
