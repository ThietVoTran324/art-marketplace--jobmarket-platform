"""Add company public page overview fields.

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-10-08 16:15:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e0f1a2b3c4d5"
down_revision: Union[str, None] = "d9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("company_type", sa.String(length=100), nullable=True))
    op.add_column("companies", sa.Column("working_days", sa.String(length=100), nullable=True))
    op.add_column("companies", sa.Column("overtime_policy", sa.String(length=100), nullable=True))
    op.add_column("companies", sa.Column("overview_text", sa.Text(), nullable=True))
    op.add_column("companies", sa.Column("why_work_here", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "why_work_here")
    op.drop_column("companies", "overview_text")
    op.drop_column("companies", "overtime_policy")
    op.drop_column("companies", "working_days")
    op.drop_column("companies", "company_type")
