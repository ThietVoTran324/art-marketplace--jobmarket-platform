"""Add company_id to comments for company page threads.

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-10-08 13:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "comments",
        sa.Column("company_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_comments_company_id",
        "comments",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_comments_company_id", "comments", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_comments_company_id", table_name="comments")
    op.drop_constraint("fk_comments_company_id", "comments", type_="foreignkey")
    op.drop_column("comments", "company_id")
