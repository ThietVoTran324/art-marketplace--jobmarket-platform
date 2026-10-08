"""Add company_follows for career-path company follow.

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-10-08 15:40:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d9e0f1a2b3c4"
down_revision: Union[str, None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_follows",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_company_follows_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_company_follows_company_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "company_id", name="pk_company_follows"),
    )
    op.create_index(
        "ix_company_follows_company_created",
        "company_follows",
        ["company_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_company_follows_company_created", table_name="company_follows")
    op.drop_table("company_follows")
