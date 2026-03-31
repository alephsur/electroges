"""Create delivery_notes and delivery_note_items tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-31
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Create delivery_note_status enum ---
    op.execute(
        "CREATE TYPE delivery_note_status AS ENUM ('draft', 'issued')"
    )

    # --- Create delivery_note_line_type enum ---
    op.execute(
        "CREATE TYPE delivery_note_line_type AS ENUM ('material', 'labor', 'other')"
    )

    # --- delivery_notes ---
    op.create_table(
        "delivery_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_note_number", sa.String(30), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "issued",
                name="delivery_note_status",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("delivery_date", sa.String(10), nullable=False),
        sa.Column("requested_by", sa.String(255), nullable=True),
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
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("delivery_note_number"),
    )
    op.create_index("ix_delivery_notes_work_order_id", "delivery_notes", ["work_order_id"])

    # --- delivery_note_items ---
    op.create_table(
        "delivery_note_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "line_type",
            postgresql.ENUM(
                "material",
                "labor",
                "other",
                name="delivery_note_line_type",
                create_type=False,
            ),
            nullable=False,
            server_default="material",
        ),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="ud"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
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
            ["delivery_note_id"], ["delivery_notes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"], ["inventory_items.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_delivery_note_items_delivery_note_id",
        "delivery_note_items",
        ["delivery_note_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_delivery_note_items_delivery_note_id", table_name="delivery_note_items")
    op.drop_table("delivery_note_items")
    op.drop_index("ix_delivery_notes_work_order_id", table_name="delivery_notes")
    op.drop_table("delivery_notes")
    op.execute("DROP TYPE delivery_note_line_type")
    op.execute("DROP TYPE delivery_note_status")
