"""Marketplace Sprint8 — bank_code, payout_attempts, payout_status widen.

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-09-28 19:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b0c1d2e3f4a5"
down_revision: Union[str, None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "seller_payment_methods",
        sa.Column("bank_code", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "pin_orders",
        sa.Column("payout_bank_code", sa.String(length=20), nullable=True),
    )

    op.execute("UPDATE pin_orders SET payout_status = 'paid' WHERE payout_status = 'manual'")

    op.drop_constraint("ck_pin_orders_payout_status", "pin_orders", type_="check")
    op.create_check_constraint(
        "ck_pin_orders_payout_status",
        "pin_orders",
        "payout_status IN ('pending', 'processing', 'paid', 'failed', 'skipped')",
    )

    op.create_table(
        "payout_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("pin_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('started', 'success', 'failed')",
            name="ck_payout_attempts_status",
        ),
    )
    op.create_index("ix_payout_attempts_order_id", "payout_attempts", ["order_id"])
    op.create_index("ix_payout_attempts_created_at", "payout_attempts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_payout_attempts_created_at", table_name="payout_attempts")
    op.drop_index("ix_payout_attempts_order_id", table_name="payout_attempts")
    op.drop_table("payout_attempts")

    op.drop_constraint("ck_pin_orders_payout_status", "pin_orders", type_="check")
    op.execute(
        "UPDATE pin_orders SET payout_status = 'manual' "
        "WHERE payout_status IN ('paid', 'processing', 'failed')"
    )
    op.create_check_constraint(
        "ck_pin_orders_payout_status",
        "pin_orders",
        "payout_status IN ('pending', 'manual', 'skipped')",
    )

    op.drop_column("pin_orders", "payout_bank_code")
    op.drop_column("seller_payment_methods", "bank_code")
