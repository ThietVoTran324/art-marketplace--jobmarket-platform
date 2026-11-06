"""Feed search Wave1: tags.name_fold + pin lookup indexes.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-11-06 11:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.api.rest.text_normalize import fold_search_text

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tags
        ADD COLUMN IF NOT EXISTS name_fold VARCHAR(100)
        """
    )

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, name FROM tags")).fetchall()
    for tag_id, name in rows:
        folded = (fold_search_text(name) or "")[:100]
        conn.execute(
            sa.text("UPDATE tags SET name_fold = :f WHERE id = :id"),
            {"f": folded, "id": tag_id},
        )

    op.execute("UPDATE tags SET name_fold = '' WHERE name_fold IS NULL")
    op.execute("ALTER TABLE tags ALTER COLUMN name_fold SET NOT NULL")

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tags_name_fold ON tags (name_fold)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pins_tags_tag_id_pin_id "
        "ON pins_tags (tag_id, pin_id DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pins_user_id_id "
        "ON pins (user_id, id DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pins_user_id_id")
    op.execute("DROP INDEX IF EXISTS ix_pins_tags_tag_id_pin_id")
    op.execute("DROP INDEX IF EXISTS ix_tags_name_fold")
    op.execute("ALTER TABLE tags DROP COLUMN IF EXISTS name_fold")
