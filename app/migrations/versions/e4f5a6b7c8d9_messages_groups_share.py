"""Messages groups, members, shared pins.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-09-29 11:50:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chats",
        sa.Column("kind", sa.String(length=20), server_default="dm", nullable=False),
    )
    op.add_column("chats", sa.Column("title", sa.String(length=120), nullable=True))
    op.add_column("chats", sa.Column("invite_code", sa.String(length=10), nullable=True))
    op.add_column("chats", sa.Column("created_by", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_chats_created_by_users",
        "chats",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_chats_invite_code", "chats", ["invite_code"], unique=True)
    op.alter_column("chats", "user_1_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("chats", "user_2_id", existing_type=sa.Integer(), nullable=True)

    op.create_table(
        "chat_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="member", nullable=False),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("chat_id", "user_id", name="uq_chat_members_chat_user"),
    )
    op.create_index("ix_chat_members_user_id", "chat_members", ["user_id"])

    # Backfill DM members from existing chats
    op.execute(
        """
        INSERT INTO chat_members (chat_id, user_id, role)
        SELECT id, user_1_id, 'member' FROM chats
        WHERE user_1_id IS NOT NULL
        ON CONFLICT (chat_id, user_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO chat_members (chat_id, user_id, role)
        SELECT id, user_2_id, 'member' FROM chats
        WHERE user_2_id IS NOT NULL
        ON CONFLICT (chat_id, user_id) DO NOTHING
        """
    )

    op.add_column(
        "messages",
        sa.Column("pin_id", sa.Integer(), sa.ForeignKey("pins.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("message_kind", sa.String(length=20), server_default="text", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("messages", "message_kind")
    op.drop_column("messages", "pin_id")
    op.drop_index("ix_chat_members_user_id", table_name="chat_members")
    op.drop_table("chat_members")
    op.drop_index("ix_chats_invite_code", table_name="chats")
    op.drop_constraint("fk_chats_created_by_users", "chats", type_="foreignkey")
    op.drop_column("chats", "created_by")
    op.drop_column("chats", "invite_code")
    op.drop_column("chats", "title")
    op.drop_column("chats", "kind")
    # leave user_1/2 nullable as-is on downgrade to avoid failing if nulls exist
