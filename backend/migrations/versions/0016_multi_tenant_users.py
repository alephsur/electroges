"""Add multi-tenancy: create tenants table, update users table.

Revision ID: 0016
Revises: 0015
Create Date: 2026-04-07 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("tax_id", sa.String(50), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Create userrole enum
    op.execute("CREATE TYPE userrole AS ENUM ('superadmin', 'admin', 'user')")

    # 3. Add new columns to users
    op.add_column("users", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "role",
            postgresql.ENUM("superadmin", "admin", "user", name="userrole", create_type=False),
            nullable=True,  # Temporarily nullable for the migration
        ),
    )
    op.add_column("users", sa.Column("invitation_token", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("invitation_expires_at", sa.DateTime(timezone=True), nullable=True))

    # 4. Migrate existing data:
    #    - Users with is_superuser=True  → role='superadmin', is_active=True (keep as is)
    #    - Users with is_superuser=False → role='user', tenant_id remains NULL for now
    #      (they will need to be assigned to a tenant manually or via data migration)
    op.execute(
        "UPDATE users SET role = 'superadmin'::userrole WHERE is_superuser = true"
    )
    op.execute(
        "UPDATE users SET role = 'user'::userrole WHERE is_superuser = false"
    )

    # 5. Make role NOT NULL now that all rows have a value
    op.alter_column("users", "role", nullable=False)

    # 6. Make hashed_password nullable (invited users have no password yet)
    op.alter_column("users", "hashed_password", nullable=True, existing_type=sa.String(255))

    # 7. Add FK constraint for tenant_id
    op.create_foreign_key(
        "fk_users_tenant_id",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 8. Add indexes
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_invitation_token", "users", ["invitation_token"])

    # 9. Drop obsolete is_superuser column
    op.drop_column("users", "is_superuser")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.execute("UPDATE users SET is_superuser = true WHERE role = 'superadmin'")

    op.drop_index("ix_users_invitation_token", table_name="users")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")

    op.alter_column("users", "hashed_password", nullable=False, existing_type=sa.String(255))
    op.drop_column("users", "invitation_expires_at")
    op.drop_column("users", "invitation_token")
    op.drop_column("users", "role")
    op.drop_column("users", "tenant_id")

    op.execute("DROP TYPE userrole")
    op.drop_table("tenants")
