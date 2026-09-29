"""job_posts/applications hiring_cycle for one-apply-per-open

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-09-26 22:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_posts",
        sa.Column("hiring_cycle", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "job_applications",
        sa.Column("hiring_cycle", sa.Integer(), nullable=False, server_default="0"),
    )
    op.drop_index("uq_job_applications_open", table_name="job_applications")
    op.create_index(
        "uq_job_applications_cycle",
        "job_applications",
        ["applicant_user_id", "job_post_id", "hiring_cycle"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_job_applications_cycle", table_name="job_applications")
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_job_applications_open "
            "ON job_applications (applicant_user_id, job_post_id) "
            "WHERE status IN ('submitted', 'viewed')"
        )
    )
    op.drop_column("job_applications", "hiring_cycle")
    op.drop_column("job_posts", "hiring_cycle")
