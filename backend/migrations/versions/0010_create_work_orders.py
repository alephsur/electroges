"""create work_orders, tasks, task_materials, work_order_purchase_orders,
certifications, certification_items; add stock_reserved to inventory_items;
add FK work_order_id to budgets

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-30 00:00:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Add stock_reserved to inventory_items ---
    op.add_column(
        "inventory_items",
        sa.Column(
            "stock_reserved",
            sa.Numeric(10, 3),
            nullable=False,
            server_default="0",
        ),
    )

    # --- Create work_order_status enum ---
    op.execute(
        "CREATE TYPE work_order_status AS ENUM "
        "('draft', 'active', 'pending_closure', 'closed', 'cancelled')"
    )

    # --- Create task_status enum ---
    op.execute(
        "CREATE TYPE task_status AS ENUM "
        "('pending', 'in_progress', 'completed', 'cancelled')"
    )

    # --- Create certification_status enum ---
    op.execute(
        "CREATE TYPE certification_status AS ENUM "
        "('draft', 'issued', 'invoiced')"
    )

    # --- work_orders ---
    op.create_table(
        "work_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_number", sa.String(20), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("origin_budget_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft", "active", "pending_closure", "closed", "cancelled",
                name="work_order_status",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("other_lines_notes", sa.Text(), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["origin_budget_id"], ["budgets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_order_number", name="uq_work_order_number"),
    )
    op.create_index("ix_work_orders_customer_id", "work_orders", ["customer_id"])
    op.create_index("ix_work_orders_status", "work_orders", ["status"])

    # --- tasks ---
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "origin_budget_line_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "in_progress", "completed", "cancelled",
                name="task_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "sort_order", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("estimated_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("actual_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["work_order_id"], ["work_orders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["origin_budget_line_id"],
            ["budget_lines.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_work_order_id", "tasks", ["work_order_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    # --- task_materials ---
    op.create_table(
        "task_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "inventory_item_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "origin_budget_line_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("estimated_quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column(
            "consumed_quantity",
            sa.Numeric(10, 3),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column("unit_cost", sa.Numeric(10, 4), nullable=False),
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
            ["task_id"], ["tasks.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"], ["inventory_items.id"]
        ),
        sa.ForeignKeyConstraint(
            ["origin_budget_line_id"],
            ["budget_lines.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_materials_task_id", "task_materials", ["task_id"])
    op.create_index(
        "ix_task_materials_inventory_item_id",
        "task_materials",
        ["inventory_item_id"],
    )

    # --- work_order_purchase_orders ---
    op.create_table(
        "work_order_purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
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
            ["work_order_id"], ["work_orders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["purchase_order_id"], ["purchase_orders.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "work_order_id",
            "purchase_order_id",
            name="uq_work_order_purchase_order",
        ),
    )
    op.create_index(
        "ix_wopo_work_order_id",
        "work_order_purchase_orders",
        ["work_order_id"],
    )
    op.create_index(
        "ix_wopo_purchase_order_id",
        "work_order_purchase_orders",
        ["purchase_order_id"],
    )

    # --- certifications ---
    op.create_table(
        "certifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("certification_number", sa.String(30), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft", "issued", "invoiced",
                name="certification_status",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["work_order_id"], ["work_orders.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "certification_number", name="uq_certification_number"
        ),
    )
    op.create_index(
        "ix_certifications_work_order_id",
        "certifications",
        ["work_order_id"],
    )

    # --- certification_items ---
    op.create_table(
        "certification_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "certification_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
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
            ["certification_id"], ["certifications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_certification_items_certification_id",
        "certification_items",
        ["certification_id"],
    )

    # --- Add FK work_order_id to budgets (column already exists, add constraint) ---
    op.create_foreign_key(
        "fk_budgets_work_order_id",
        "budgets",
        "work_orders",
        ["work_order_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_budgets_work_order_id", "budgets", type_="foreignkey"
    )
    op.drop_table("certification_items")
    op.drop_table("certifications")
    op.drop_table("work_order_purchase_orders")
    op.drop_table("task_materials")
    op.drop_table("tasks")
    op.drop_table("work_orders")
    op.drop_column("inventory_items", "stock_reserved")
    op.execute("DROP TYPE IF EXISTS work_order_status")
    op.execute("DROP TYPE IF EXISTS task_status")
    op.execute("DROP TYPE IF EXISTS certification_status")
