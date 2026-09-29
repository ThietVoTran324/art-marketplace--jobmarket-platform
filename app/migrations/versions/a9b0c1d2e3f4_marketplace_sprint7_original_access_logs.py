"""Marketplace Sprint7 — original access audit log.

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-09-28 17:40:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pin_original_access_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "pin_id",
            sa.Integer(),
            sa.ForeignKey("pins.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=400), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('mint', 'file')",
            name="ck_pin_original_access_logs_action",
        ),
    )
    op.create_index(
        "ix_pin_original_access_logs_pin_id",
        "pin_original_access_logs",
        ["pin_id"],
    )
    op.create_index(
        "ix_pin_original_access_logs_user_id",
        "pin_original_access_logs",
        ["user_id"],
    )
    op.create_index(
        "ix_pin_original_access_logs_created_at",
        "pin_original_access_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pin_original_access_logs_created_at", table_name="pin_original_access_logs")
    op.drop_index("ix_pin_original_access_logs_user_id", table_name="pin_original_access_logs")
    op.drop_index("ix_pin_original_access_logs_pin_id", table_name="pin_original_access_logs")
    op.drop_table("pin_original_access_logs")
