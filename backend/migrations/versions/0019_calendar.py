"""Add calendar: start_date/end_date to work_orders, calendar_events table.

Revision ID: 0019
Revises: 0018
Create Date: 2026-04-09 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add start_date and end_date to work_orders
    op.add_column("work_orders", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("work_orders", sa.Column("end_date", sa.Date(), nullable=True))

    # Create calendar_events table
    op.create_table(
        "calendar_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_datetime", sa.String(32), nullable=False),
        sa.Column("end_datetime", sa.String(32), nullable=True),
        sa.Column("all_day", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("color", sa.String(20), nullable=False, server_default="#8b5cf6"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
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
    )
    op.create_index("ix_calendar_events_tenant_id", "calendar_events", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_calendar_events_tenant_id", table_name="calendar_events")
    op.drop_table("calendar_events")
    op.drop_column("work_orders", "end_date")
    op.drop_column("work_orders", "start_date")
