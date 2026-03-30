"""PDF rendering utilities using Jinja2 + WeasyPrint."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


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


def render_budget_pdf_html(budget, company, totals, customer, address, lines) -> str:
    """
    Renders the budget PDF HTML using the Jinja2 template.

    IMPORTANT: `lines` must be BudgetLinePublicResponse instances —
    they must NOT contain unit_cost or margin fields.
    """
    env = _get_jinja_env()
    template = env.get_template("budget_pdf.html")

    has_line_discounts = any(float(line.line_discount_pct) > 0 for line in lines)

    # Build absolute path for logo so WeasyPrint can find it
    logo_abs_path = None
    if company.logo_path:
        logo_abs_path = str(Path(company.logo_path).resolve())

    return template.render(
        budget=budget,
        company=company,
        totals=totals,
        customer=customer,
        address=address,
        lines=lines,
        has_line_discounts=has_line_discounts,
        logo_abs_path=logo_abs_path,
    )
