"""create customers, customer_addresses, customer_documents tables

Revision ID: 0006
Revises: 0005
Create Date: 2025-01-01 00:00:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum types
    op.execute("CREATE TYPE customertype AS ENUM ('individual', 'company', 'community')")
    op.execute("CREATE TYPE addresstype AS ENUM ('fiscal', 'service')")

    # Table customers
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "customer_type",
            sa.VARCHAR(20),
            nullable=False,
            server_default="individual",
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("tax_id", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("phone_secondary", sa.String(30), nullable=True),
        sa.Column("contact_person", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.UniqueConstraint("tax_id", name="uq_customers_tax_id"),
    )
    op.create_index("ix_customers_name", "customers", ["name"])
    op.create_index("ix_customers_is_active", "customers", ["is_active"])

    # Table customer_addresses
    op.create_table(
        "customer_addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "address_type",
            sa.VARCHAR(20),
            nullable=False,
            server_default="service",
        ),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("street", sa.String(255), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("postal_code", sa.String(10), nullable=False),
        sa.Column("province", sa.String(100), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_addresses_customer_id", "customer_addresses", ["customer_id"])

    # Table customer_documents
    op.create_table(
        "customer_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=False, server_default="other"),
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
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_documents_customer_id", "customer_documents", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_customer_documents_customer_id", table_name="customer_documents")
    op.drop_table("customer_documents")
    op.drop_index("ix_customer_addresses_customer_id", table_name="customer_addresses")
    op.drop_table("customer_addresses")
    op.drop_index("ix_customers_is_active", table_name="customers")
    op.drop_index("ix_customers_name", table_name="customers")
    op.drop_table("customers")
    op.execute("DROP TYPE IF EXISTS addresstype")
    op.execute("DROP TYPE IF EXISTS customertype")
