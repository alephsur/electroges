"""create site_visits, site_visit_materials, site_visit_photos, site_visit_documents

Revision ID: 0007
Revises: 0006
Create Date: 2025-01-01 00:00:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE sitevisit_status AS ENUM "
        "('scheduled', 'in_progress', 'completed', 'cancelled', 'no_show')"
    )

    op.create_table(
        "site_visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_address_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("address_text", sa.String(500), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(30), nullable=True),
        sa.Column("visit_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estimated_duration_hours", sa.Numeric(4, 1), nullable=True),
        sa.Column("status", sa.VARCHAR(20), nullable=False, server_default="scheduled"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("work_scope", sa.Text(), nullable=True),
        sa.Column("technical_notes", sa.Text(), nullable=True),
        sa.Column("estimated_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("estimated_budget", sa.Numeric(10, 2), nullable=True),
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
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["customer_address_id"], ["customer_addresses.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_site_visits_customer_id", "site_visits", ["customer_id"])
    op.create_index("ix_site_visits_visit_date", "site_visits", ["visit_date"])
    op.create_index("ix_site_visits_status", "site_visits", ["status"])

    op.create_table(
        "site_visit_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("estimated_qty", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("unit_cost", sa.Numeric(10, 4), nullable=True),
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
            ["site_visit_id"], ["site_visits.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"], ["inventory_items.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_site_visit_materials_site_visit_id",
        "site_visit_materials",
        ["site_visit_id"],
    )

    op.create_table(
        "site_visit_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("caption", sa.String(255), nullable=True),
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
            ["site_visit_id"], ["site_visits.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_site_visit_photos_site_visit_id",
        "site_visit_photos",
        ["site_visit_id"],
    )

    op.create_table(
        "site_visit_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "document_type", sa.String(50), nullable=False, server_default="other"
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
            ["site_visit_id"], ["site_visits.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_site_visit_documents_site_visit_id",
        "site_visit_documents",
        ["site_visit_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_site_visit_documents_site_visit_id", "site_visit_documents")
    op.drop_table("site_visit_documents")
    op.drop_index("ix_site_visit_photos_site_visit_id", "site_visit_photos")
    op.drop_table("site_visit_photos")
    op.drop_index("ix_site_visit_materials_site_visit_id", "site_visit_materials")
    op.drop_table("site_visit_materials")
    op.drop_index("ix_site_visits_status", "site_visits")
    op.drop_index("ix_site_visits_visit_date", "site_visits")
    op.drop_index("ix_site_visits_customer_id", "site_visits")
    op.drop_table("site_visits")
    op.execute("DROP TYPE sitevisit_status")
