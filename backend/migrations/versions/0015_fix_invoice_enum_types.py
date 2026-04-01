"""Fix invoice status, invoice_line_origin and payment_method columns to use
   native PostgreSQL enum types instead of VARCHAR.

Revision ID: 0015
Revises: 0014
Create Date: 2025-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create native enum types
    op.execute(
        "CREATE TYPE invoice_status AS ENUM ('draft', 'sent', 'paid', 'cancelled')"
    )
    op.execute(
        "CREATE TYPE invoice_line_origin AS ENUM ('certification', 'task', 'manual')"
    )
    op.execute(
        "CREATE TYPE payment_method AS ENUM ('transfer', 'cash', 'card', 'direct_debit')"
    )

    # Drop server defaults before altering types (PostgreSQL cannot cast
    # a string default to an enum type automatically)
    op.execute("ALTER TABLE invoices ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE invoice_lines ALTER COLUMN origin_type DROP DEFAULT")

    # Alter invoices.status
    op.execute(
        "ALTER TABLE invoices "
        "ALTER COLUMN status TYPE invoice_status USING status::invoice_status"
    )

    # Restore default as enum literal
    op.execute(
        "ALTER TABLE invoices ALTER COLUMN status SET DEFAULT 'draft'::invoice_status"
    )

    # Alter invoice_lines.origin_type
    op.execute(
        "ALTER TABLE invoice_lines "
        "ALTER COLUMN origin_type TYPE invoice_line_origin "
        "USING origin_type::invoice_line_origin"
    )

    # Restore default as enum literal
    op.execute(
        "ALTER TABLE invoice_lines "
        "ALTER COLUMN origin_type SET DEFAULT 'manual'::invoice_line_origin"
    )

    # Alter payments.method (no server_default in migration 0014)
    op.execute(
        "ALTER TABLE payments "
        "ALTER COLUMN method TYPE payment_method USING method::payment_method"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE invoices ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE invoice_lines ALTER COLUMN origin_type DROP DEFAULT")

    op.execute(
        "ALTER TABLE payments "
        "ALTER COLUMN method TYPE VARCHAR(20) USING method::VARCHAR"
    )
    op.execute(
        "ALTER TABLE invoice_lines "
        "ALTER COLUMN origin_type TYPE VARCHAR(20) USING origin_type::VARCHAR"
    )
    op.execute(
        "ALTER TABLE invoice_lines ALTER COLUMN origin_type SET DEFAULT 'manual'"
    )
    op.execute(
        "ALTER TABLE invoices "
        "ALTER COLUMN status TYPE VARCHAR(20) USING status::VARCHAR"
    )
    op.execute("ALTER TABLE invoices ALTER COLUMN status SET DEFAULT 'draft'")

    op.execute("DROP TYPE payment_method")
    op.execute("DROP TYPE invoice_line_origin")
    op.execute("DROP TYPE invoice_status")
