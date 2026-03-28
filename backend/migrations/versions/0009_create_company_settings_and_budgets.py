"""create company_settings, budgets, budget_lines

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-27 00:00:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── company_settings — singleton ──────────────────────────────────────────
    op.create_table(
        "company_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("tax_id", sa.String(20), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(10), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("bank_account", sa.String(50), nullable=True),
        sa.Column("logo_path", sa.String(500), nullable=True),
        sa.Column("general_conditions", sa.Text(), nullable=True),
        sa.Column(
            "default_tax_rate",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="21.00",
        ),
        sa.Column(
            "default_validity_days",
            sa.Integer(),
            nullable=False,
            server_default="30",
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
        sa.PrimaryKeyConstraint("id"),
    )
    # Insert empty singleton record
    op.execute("INSERT INTO company_settings (id) VALUES (1)")

    # ── budget_status enum ────────────────────────────────────────────────────
    op.execute(
        "CREATE TYPE budget_status AS ENUM "
        "('draft', 'sent', 'accepted', 'rejected', 'expired')"
    )

    # ── budget_line_type enum ─────────────────────────────────────────────────
    op.execute(
        "CREATE TYPE budget_line_type AS ENUM "
        "('labor', 'material', 'other')"
    )

    # ── budgets ───────────────────────────────────────────────────────────────
    op.create_table(
        "budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("budget_number", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_budget_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "is_latest_version", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.VARCHAR(20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column(
            "tax_rate", sa.Numeric(5, 2), nullable=False, server_default="21.00"
        ),
        sa.Column(
            "discount_pct", sa.Numeric(5, 2), nullable=False, server_default="0.00"
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("client_notes", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        # work_order_id — FK added in WorkOrder migration
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["site_visit_id"], ["site_visits.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["parent_budget_id"], ["budgets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("budget_number", name="uq_budget_number"),
    )
    op.create_index("ix_budgets_customer_id", "budgets", ["customer_id"])
    op.create_index("ix_budgets_status", "budgets", ["status"])
    op.create_index("ix_budgets_issue_date", "budgets", ["issue_date"])

    # ── budget_lines ──────────────────────────────────────────────────────────
    op.create_table(
        "budget_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("budget_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_type", sa.VARCHAR(20), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("unit_price", sa.Numeric(10, 4), nullable=False),
        sa.Column(
            "unit_cost",
            sa.Numeric(10, 4),
            nullable=False,
            server_default="0.0",
        ),
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
            ["budget_id"], ["budgets.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"], ["inventory_items.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budget_lines_budget_id", "budget_lines", ["budget_id"])


def downgrade() -> None:
    op.drop_index("ix_budget_lines_budget_id", "budget_lines")
    op.drop_table("budget_lines")
    op.drop_index("ix_budgets_issue_date", "budgets")
    op.drop_index("ix_budgets_status", "budgets")
    op.drop_index("ix_budgets_customer_id", "budgets")
    op.drop_table("budgets")
    op.execute("DROP TYPE budget_line_type")
    op.execute("DROP TYPE budget_status")
    op.drop_table("company_settings")
