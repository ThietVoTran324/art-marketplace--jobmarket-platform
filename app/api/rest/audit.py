from datetime import datetime

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.postgresql.models import AuditLogOrm

ACTION_ADMIN_DELETE_PIN = "admin_delete_pin"
ACTION_ADMIN_DELETE_COMMENT = "admin_delete_comment"
ACTION_ROLE_ASSIGN = "role_assign"
ACTION_ROLE_REVOKE = "role_revoke"
ACTION_KYC_SUBMIT = "kyc_submit"
ACTION_KYC_APPROVE = "kyc_approve"
ACTION_KYC_REJECT = "kyc_reject"
ACTION_KYC_NEED_MORE_INFO = "kyc_need_more_info"
ACTION_WORK_EXP_APPROVE = "work_exp_approve"
ACTION_WORK_EXP_REJECT = "work_exp_reject"
ACTION_JOB_REPORT_CREATE = "job_report_create"
ACTION_JOB_REPORT_DISMISS = "job_report_dismiss"
ACTION_JOB_REPORT_ACTIONED = "job_report_actioned"
ACTION_COMPANY_SUSPEND = "company_suspend"
ACTION_COMPANY_UNSUSPEND = "company_unsuspend"
ACTION_COPYRIGHT_REPORT_RESOLVE = "copyright_report_resolve"
ACTION_COPYRIGHT_REPORT_DISMISS = "copyright_report_dismiss"
ACTION_PAYMENT_METHOD_VERIFY = "payment_method_verify"
ACTION_SELLER_PAYOUT_MARK = "seller_payout_mark"

VALID_ACTIONS = frozenset(
    {
        ACTION_ADMIN_DELETE_PIN,
        ACTION_ADMIN_DELETE_COMMENT,
        ACTION_ROLE_ASSIGN,
        ACTION_ROLE_REVOKE,
        ACTION_KYC_SUBMIT,
        ACTION_KYC_APPROVE,
        ACTION_KYC_REJECT,
        ACTION_KYC_NEED_MORE_INFO,
        ACTION_WORK_EXP_APPROVE,
        ACTION_WORK_EXP_REJECT,
        ACTION_JOB_REPORT_CREATE,
        ACTION_JOB_REPORT_DISMISS,
        ACTION_JOB_REPORT_ACTIONED,
        ACTION_COMPANY_SUSPEND,
        ACTION_COMPANY_UNSUSPEND,
        ACTION_COPYRIGHT_REPORT_RESOLVE,
        ACTION_COPYRIGHT_REPORT_DISMISS,
        ACTION_PAYMENT_METHOD_VERIFY,
        ACTION_SELLER_PAYOUT_MARK,
    }
)

TARGET_PIN = "pin"
TARGET_COMMENT = "comment"
TARGET_USER = "user"
TARGET_KYC_REQUEST = "kyc_request"
TARGET_COMPANY = "company"
TARGET_WORK_EXP = "work_experience"
TARGET_JOB_REPORT = "job_report"
TARGET_JOB_POST = "job_post"
TARGET_COPYRIGHT_REPORT = "copyright_report"
TARGET_PAYMENT_METHOD = "payment_method"
TARGET_PIN_ORDER = "pin_order"


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    actor_user_id: int | None
    action: str
    target_type: str
    target_id: int | None
    metadata: dict = Field(default_factory=dict, validation_alias="meta")


async def write_audit(
    db: AsyncSession,
    actor_user_id: int | None,
    action: str,
    target_type: str,
    target_id: int | None,
    metadata: dict | None = None,
) -> None:
    """Append an audit record in the caller's transaction. Caller commits."""
    if action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"unknown audit action: {action}",
        )

    await db.execute(
        insert(AuditLogOrm).values(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            meta=metadata or {},
        )
    )
    await db.flush()
