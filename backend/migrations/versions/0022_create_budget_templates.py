"""Create budget_templates, budget_template_sections and budget_template_lines.

Templates are reusable budget blueprints per tenant, organised into optional
sections and a list of predefined lines (with unit_cost kept internally).

Revision ID: 0022
Revises: 0021
Create Date: 2026-04-23 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "budget_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_budget_templates_tenant_name"),
    )
    op.create_index(
        "ix_budget_templates_tenant_id",
        "budget_templates",
        ["tenant_id"],
    )

    op.create_table(
        "budget_template_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
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
            ["template_id"], ["budget_templates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_budget_template_sections_template_id",
        "budget_template_sections",
        ["template_id"],
    )

    op.create_table(
        "budget_template_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "line_type",
            postgresql.ENUM(
                "labor",
                "material",
                "other",
                name="budget_line_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("unit_price", sa.Numeric(10, 4), nullable=False),
        sa.Column(
            "unit_cost", sa.Numeric(10, 4), nullable=False, server_default="0.0"
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
            ["template_id"], ["budget_templates.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["section_id"], ["budget_template_sections.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_budget_template_lines_template_id",
        "budget_template_lines",
        ["template_id"],
    )
    op.create_index(
        "ix_budget_template_lines_section_id",
        "budget_template_lines",
        ["section_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_budget_template_lines_section_id", table_name="budget_template_lines"
    )
    op.drop_index(
        "ix_budget_template_lines_template_id", table_name="budget_template_lines"
    )
    op.drop_table("budget_template_lines")

    op.drop_index(
        "ix_budget_template_sections_template_id",
        table_name="budget_template_sections",
    )
    op.drop_table("budget_template_sections")

    op.drop_index("ix_budget_templates_tenant_id", table_name="budget_templates")
    op.drop_table("budget_templates")
