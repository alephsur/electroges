"""fix site_visits.status column type from VARCHAR to sitevisit_status enum

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-26 00:00:00

"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE site_visits ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE site_visits "
        "ALTER COLUMN status TYPE sitevisit_status "
        "USING status::sitevisit_status"
    )
    op.execute(
        "ALTER TABLE site_visits "
        "ALTER COLUMN status SET DEFAULT 'scheduled'::sitevisit_status"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE site_visits ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE site_visits "
        "ALTER COLUMN status TYPE VARCHAR(20) "
        "USING status::VARCHAR"
    )
    op.execute(
        "ALTER TABLE site_visits ALTER COLUMN status SET DEFAULT 'scheduled'"
    )
