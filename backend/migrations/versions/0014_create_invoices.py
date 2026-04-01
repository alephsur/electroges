"""create invoices, invoice_lines, payments + FK certification.invoice_id
   + company_settings.default_payment_days

Revision ID: 0014
Revises: 0013
Create Date: 2025-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add default_payment_days to company_settings
    op.add_column(
        "company_settings",
        sa.Column(
            "default_payment_days",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
    )

    # Create invoices table
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.String(25), nullable=False),
        sa.Column(
            "is_rectification",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "rectifies_invoice_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "customer_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "work_order_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "tax_rate",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="21.00",
        ),
        sa.Column(
            "discount_pct",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("client_notes", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(
            ["work_order_id"], ["work_orders.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["rectifies_invoice_id"], ["invoices.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number", name="uq_invoice_number"),
    )
    op.create_index("ix_invoices_customer_id", "invoices", ["customer_id"])
    op.create_index(
        "ix_invoices_work_order_id", "invoices", ["work_order_id"]
    )
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_issue_date", "invoices", ["issue_date"])
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"])

    # Create invoice_lines table
    op.create_table(
        "invoice_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "invoice_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "origin_type",
            sa.String(20),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "origin_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "sort_order", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("unit_price", sa.Numeric(10, 4), nullable=False),
        sa.Column(
            "line_discount_pct",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["invoices.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"]
    )

    # Create payments table
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "invoice_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["invoices.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payments_invoice_id", "payments", ["invoice_id"]
    )

    # Add FK from certifications.invoice_id to invoices.id
    op.create_foreign_key(
        "fk_certifications_invoice_id",
        "certifications",
        "invoices",
        ["invoice_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_certifications_invoice_id", "certifications", type_="foreignkey"
    )
    op.drop_index("ix_payments_invoice_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index(
        "ix_invoice_lines_invoice_id", table_name="invoice_lines"
    )
    op.drop_table("invoice_lines")
    op.drop_index("ix_invoices_due_date", table_name="invoices")
    op.drop_index("ix_invoices_issue_date", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_invoices_work_order_id", table_name="invoices")
    op.drop_index("ix_invoices_customer_id", table_name="invoices")
    op.drop_table("invoices")
    op.drop_column("company_settings", "default_payment_days")
