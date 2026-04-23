"""Create budget_sections table and add section_id to budget_lines.

Sections are optional: both budget_lines.section_id and budgets without sections
remain fully valid. This preserves backward compatibility with existing budgets.

Revision ID: 0021
Revises: 0020
Create Date: 2026-04-21 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "budget_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("budget_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
            ["budget_id"], ["budgets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_budget_sections_budget_id",
        "budget_sections",
        ["budget_id"],
    )

    op.add_column(
        "budget_lines",
        sa.Column(
            "section_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "budget_lines_section_id_fkey",
        "budget_lines",
        "budget_sections",
        ["section_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_budget_lines_section_id",
        "budget_lines",
        ["section_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_budget_lines_section_id", table_name="budget_lines")
    op.drop_constraint(
        "budget_lines_section_id_fkey",
        "budget_lines",
        type_="foreignkey",
    )
    op.drop_column("budget_lines", "section_id")

    op.drop_index("ix_budget_sections_budget_id", table_name="budget_sections")
    op.drop_table("budget_sections")
