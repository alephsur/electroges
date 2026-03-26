"""supplier_items, stock_movements, inventory_item extensions

Revision ID: 0005
Revises: 0004
Create Date: 2025-01-01 00:00:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Table supplier_items
    op.create_table(
        "supplier_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_ref", sa.String(100), nullable=True),
        sa.Column("unit_cost", sa.Numeric(10, 4), nullable=False),
        sa.Column("last_purchase_cost", sa.Numeric(10, 4), nullable=True),
        sa.Column("last_purchase_date", sa.Date(), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column(
            "is_preferred",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_id", "inventory_item_id", name="uq_supplier_item"),
    )
    op.create_index(
        "ix_supplier_items_supplier_id", "supplier_items", ["supplier_id"]
    )
    op.create_index(
        "ix_supplier_items_inventory_item_id", "supplier_items", ["inventory_item_id"]
    )

    # 2. Table stock_movements
    op.create_table(
        "stock_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", sa.VARCHAR(20), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(10, 4), nullable=False),
        sa.Column("reference_type", sa.VARCHAR(30), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_stock_movements_inventory_item_id",
        "stock_movements",
        ["inventory_item_id"],
    )
    op.create_index(
        "ix_stock_movements_reference",
        "stock_movements",
        ["reference_type", "reference_id"],
    )

    # 3. New column in inventory_items: weighted average cost
    op.add_column(
        "inventory_items",
        sa.Column(
            "unit_cost_avg",
            sa.Numeric(10, 4),
            nullable=False,
            server_default="0.0",
        ),
    )

    # 4. New column in purchase_order_lines: link to supplier price record
    op.add_column(
        "purchase_order_lines",
        sa.Column(
            "supplier_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_pol_supplier_item",
        "purchase_order_lines",
        "supplier_items",
        ["supplier_item_id"],
        ["id"],
    )

    # 5. Data migration: convert existing supplier_id relationships to SupplierItem rows.
    # For each inventory_item that has a supplier_id, create a SupplierItem with
    # is_preferred=true and unit_cost equal to the item's unit_cost.
    # This preserves all existing configuration without data loss.
    op.execute("""
        INSERT INTO supplier_items (
            id, supplier_id, inventory_item_id,
            unit_cost, is_preferred, is_active,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            ii.supplier_id,
            ii.id,
            ii.unit_cost,
            true,
            true,
            now(),
            now()
        FROM inventory_items ii
        WHERE ii.supplier_id IS NOT NULL
    """)

    # 6. Initialise unit_cost_avg from existing unit_cost
    op.execute("""
        UPDATE inventory_items
        SET unit_cost_avg = unit_cost
        WHERE unit_cost > 0
    """)


def downgrade() -> None:
    op.drop_constraint(
        "fk_pol_supplier_item", "purchase_order_lines", type_="foreignkey"
    )
    op.drop_column("purchase_order_lines", "supplier_item_id")
    op.drop_column("inventory_items", "unit_cost_avg")
    op.drop_index("ix_stock_movements_reference", table_name="stock_movements")
    op.drop_index(
        "ix_stock_movements_inventory_item_id", table_name="stock_movements"
    )
    op.drop_table("stock_movements")
    op.drop_index(
        "ix_supplier_items_inventory_item_id", table_name="supplier_items"
    )
    op.drop_index("ix_supplier_items_supplier_id", table_name="supplier_items")
    op.drop_table("supplier_items")
