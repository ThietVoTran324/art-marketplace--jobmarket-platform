"""Marketplace Sprint6 — payment method verification_status

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-09-27 18:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "d6e7f8a9b0c1"
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
)


def upgrade() -> None:
    op.add_column(
        "seller_payment_methods",
        sa.Column(
            "verification_status",
            sa.String(length=20),
            nullable=False,
            server_default="unverified",
        ),
    )
    op.add_column(
        "seller_payment_methods",
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "seller_payment_methods",
        sa.Column("verified_by", sa.String(length=64), nullable=True),
    )
    op.create_check_constraint(
        "ck_seller_payment_methods_verification_status",
        "seller_payment_methods",
        "verification_status IN ('unverified', 'verified')",
    )
    op.create_index(
        "ix_seller_payment_methods_user_active_verified",
        "seller_payment_methods",
        ["user_id", "is_active", "verification_status"],
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

    op.drop_index(
        "ix_seller_payment_methods_user_active_verified",
        table_name="seller_payment_methods",
    )
    op.drop_constraint(
        "ck_seller_payment_methods_verification_status",
        "seller_payment_methods",
        type_="check",
    )
    op.drop_column("seller_payment_methods", "verified_by")
    op.drop_column("seller_payment_methods", "verified_at")
    op.drop_column("seller_payment_methods", "verification_status")
