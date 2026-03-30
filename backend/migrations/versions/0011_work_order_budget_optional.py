"""Make work_order origin_budget_id nullable (direct work order creation)

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-30
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("work_orders", "origin_budget_id", nullable=True)


def downgrade() -> None:
    # NOTE: rows with NULL origin_budget_id will fail this downgrade
    op.alter_column("work_orders", "origin_budget_id", nullable=False)
