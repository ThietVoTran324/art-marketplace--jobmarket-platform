"""Add users_saved_jobs association (save JD like pins).

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-10-08 14:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users_saved_jobs",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_post_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_users_saved_jobs_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_post_id"],
            ["job_posts.id"],
            name="fk_users_saved_jobs_job_post_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "job_post_id", name="pk_users_saved_jobs"),
    )
    op.create_index(
        "ix_users_saved_jobs_user_created",
        "users_saved_jobs",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_users_saved_jobs_user_created", table_name="users_saved_jobs")
    op.drop_table("users_saved_jobs")
