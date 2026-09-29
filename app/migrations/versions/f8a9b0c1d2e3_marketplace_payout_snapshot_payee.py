"""Marketplace Sprint6b — order payout snapshot + platform payee display

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-09-27 21:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_AUDIT = (
    "admin_delete_pin",
    "admin_delete_comment",
    "role_assign",
    "role_revoke",
    "kyc_submit",
    "kyc_approve",
    "kyc_reject",
    "kyc_need_more_info",
    "work_exp_approve",
    "work_exp_reject",
    "job_report_create",
    "job_report_dismiss",
    "job_report_actioned",
    "company_suspend",
    "company_unsuspend",
    "copyright_report_resolve",
    "copyright_report_dismiss",
    "payment_method_verify",
    "seller_payout_mark",
)

OLD_AUDIT = (
    "admin_delete_pin",
    "admin_delete_comment",
    "role_assign",
    "role_revoke",
    "kyc_submit",
    "kyc_approve",
    "kyc_reject",
    "kyc_need_more_info",
    "work_exp_approve",
    "work_exp_reject",
    "job_report_create",
    "job_report_dismiss",
    "job_report_actioned",
    "company_suspend",
    "company_unsuspend",
    "copyright_report_resolve",
    "copyright_report_dismiss",
    "payment_method_verify",
)


def upgrade() -> None:
    op.add_column(
        "pin_orders",
        sa.Column("payout_method_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "pin_orders",
        sa.Column("payout_display_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "pin_orders",
        sa.Column("payout_account_identifier", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "pin_orders",
        sa.Column("payout_bank_name", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "pin_orders",
        sa.Column("payout_account_holder", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "pin_orders",
        sa.Column("payout_amount_vnd", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pin_orders",
        sa.Column("payout_marked_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "pin_orders",
        sa.Column("payout_note", sa.String(length=500), nullable=True),
    )

    op.drop_constraint("ck_audit_logs_action", "audit_logs", type_="check")
    op.create_check_constraint(
        "ck_audit_logs_action",
        "audit_logs",
        "action IN ('{}')".format("', '".join(NEW_AUDIT)),
    )


def downgrade() -> None:
    op.drop_constraint("ck_audit_logs_action", "audit_logs", type_="check")
    op.create_check_constraint(
        "ck_audit_logs_action",
        "audit_logs",
        "action IN ('{}')".format("', '".join(OLD_AUDIT)),
    )
    for col in (
        "payout_note",
        "payout_marked_at",
        "payout_amount_vnd",
        "payout_account_holder",
        "payout_bank_name",
        "payout_account_identifier",
        "payout_display_name",
        "payout_method_type",
    ):
        op.drop_column("pin_orders", col)
