"""Drop deprecated supplier_id and unit_cost columns from inventory_items.

These columns were superseded by the SupplierItem junction table (migration 0005).
unit_cost_avg (PMP) is now the authoritative cost field on InventoryItem.

Revision ID: 0020
Revises: 0019
Create Date: 2026-04-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the legacy FK index and constraint, then the column
    op.drop_index("ix_inventory_items_supplier_id", table_name="inventory_items")
    op.drop_constraint(
        "inventory_items_supplier_id_fkey",
        "inventory_items",
        type_="foreignkey",
    )
    op.drop_column("inventory_items", "supplier_id")

    # Drop the legacy unit_cost column (PMP lives in unit_cost_avg)
    op.drop_column("inventory_items", "unit_cost")


def downgrade() -> None:
    op.add_column(
        "inventory_items",
        sa.Column(
            "unit_cost",
            sa.Numeric(10, 4),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "inventory_items",
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "inventory_items_supplier_id_fkey",
        "inventory_items",
        "suppliers",
        ["supplier_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_inventory_items_supplier_id",
        "inventory_items",
        ["supplier_id"],
    )
