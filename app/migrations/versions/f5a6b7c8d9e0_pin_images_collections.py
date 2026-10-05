"""Pin images for multi-image collections.

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-10-05 12:15:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pin_images",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("pin_id", sa.Integer(), nullable=False),
        sa.Column("image", sa.String(length=200), nullable=True),
        sa.Column("original_image", sa.String(length=200), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["pin_id"], ["pins.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("pin_id", "sort_order", name="uq_pin_images_pin_sort"),
    )
    op.create_index("ix_pin_images_pin_id", "pin_images", ["pin_id"])

    # Backfill one row per existing pin that has media
    op.execute(
        """
        INSERT INTO pin_images (pin_id, image, original_image, sort_order, created_at)
        SELECT id, image, original_image, 0, COALESCE NOW() AT TIME ZONE 'utc'
        FROM pins
        WHERE image IS NOT NULL OR original_image IS NOT NULL OR "videoPreview" IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_pin_images_pin_id", table_name="pin_images")
    op.drop_table("pin_images")
