from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rest.audit import (
    ACTION_ADMIN_DELETE_COMMENT,
    ACTION_ADMIN_DELETE_PIN,
    ACTION_COPYRIGHT_REPORT_DISMISS,
    ACTION_COPYRIGHT_REPORT_RESOLVE,
    ACTION_PAYMENT_METHOD_VERIFY,
    ACTION_ROLE_ASSIGN,
    ACTION_ROLE_REVOKE,
    ACTION_SELLER_PAYOUT_MARK,
    TARGET_COMMENT,
    TARGET_COPYRIGHT_REPORT,
    TARGET_PAYMENT_METHOD,
    TARGET_PIN,
    TARGET_PIN_ORDER,
    TARGET_USER,
    AuditLogOut,
    write_audit,
)
from app.api.rest.dependencies import db, require_roles
from app.api.rest.marketplace.payment_methods import set_method_verification
from app.api.rest.marketplace.payout_service import (
    execute_order_payout,
    mark_payout_paid_manual,
)
from app.api.rest.marketplace.schemas import (
    AdminPaymentMethodVerifyIn,
    AdminPayoutExecuteIn,
    AdminPayoutMarkIn,
    AdminPayoutOut,
    CopyrightReportAdminPatchIn,
    CopyrightReportOut,
    PaymentMethodOut,
)
from app.api.rest.roles import assign_role, revoke_role
from app.postgresql.models import (
    AuditLogOrm,
    CommentsOrm,
    CompanyVerificationRequestsOrm,
    CopyrightReportsOrm,
    JobPostReportsOrm,
    PinListingsOrm,
    PinOrdersOrm,
    PinsOrm,
    SellerPaymentMethodsOrm,
    UsersOrm,
    WorkExperiencesOrm,
)

router = APIRouter(prefix="/admin", tags=["admin"])


class RoleAssignIn(BaseModel):
    role: str = Field(..., min_length=1, max_length=50)


class AdminOverviewOut(BaseModel):
    audit_events_24h: int
    open_copyright_reports: int
    open_job_reports: int
    open_kyc_requests: int
    open_work_exp_pending: int
    unverified_payment_methods: int = 0


class AdminPaymentMethodOut(PaymentMethodOut):
    user_id: int
    username: str


async def _require_other_user(
    db: AsyncSession, admin_user_id: int, target_user_id: int
) -> UsersOrm:
    if admin_user_id == target_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cannot modify your own roles",
        )

    target = await db.scalar(select(UsersOrm).where(UsersOrm.id == target_user_id))
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return target


@router.get("/overview", response_model=AdminOverviewOut)
async def admin_overview(
    db: db,
    _: int = Depends(require_roles("admin")),
):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    audit_events_24h = await db.scalar(
        select(func.count())
        .select_from(AuditLogOrm)
        .where(AuditLogOrm.created_at >= since)
    )
    open_copyright_reports = await db.scalar(
        select(func.count())
        .select_from(CopyrightReportsOrm)
        .where(CopyrightReportsOrm.status == "open")
    )
    open_job_reports = await db.scalar(
        select(func.count())
        .select_from(JobPostReportsOrm)
        .where(JobPostReportsOrm.status == "open")
    )
    open_kyc_requests = await db.scalar(
        select(func.count())
        .select_from(CompanyVerificationRequestsOrm)
        .where(
            CompanyVerificationRequestsOrm.status.in_(("pending", "need_more_info"))
        )
    )
    open_work_exp_pending = await db.scalar(
        select(func.count())
        .select_from(WorkExperiencesOrm)
        .where(WorkExperiencesOrm.status == "pending")
    )
    unverified_payment_methods = await db.scalar(
        select(func.count())
        .select_from(SellerPaymentMethodsOrm)
        .where(
            SellerPaymentMethodsOrm.verification_status == "unverified",
            SellerPaymentMethodsOrm.is_active.is_(True),
        )
    )
    return AdminOverviewOut(
        audit_events_24h=int(audit_events_24h or 0),
        open_copyright_reports=int(open_copyright_reports or 0),
        open_job_reports=int(open_job_reports or 0),
        open_kyc_requests=int(open_kyc_requests or 0),
        open_work_exp_pending=int(open_work_exp_pending or 0),
        unverified_payment_methods=int(unverified_payment_methods or 0),
    )


@router.delete("/pin/{pin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_pin(
    pin_id: int,
    db: db,
    admin_user_id: int = Depends(require_roles("admin")),
):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    owner_user_id = pin.user_id

    await db.execute(delete(PinsOrm).where(PinsOrm.id == pin_id))
    await write_audit(
        db,
        actor_user_id=admin_user_id,
        action=ACTION_ADMIN_DELETE_PIN,
        target_type=TARGET_PIN,
        target_id=pin_id,
        metadata={"owner_user_id": owner_user_id},
    )
    await db.commit()


@router.delete("/comment/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_copmment(
    comment_id: int,
    db: db,
    admin_user_id: int = Depends(require_roles("admin")),
):
    comment = await db.scalar(select(CommentsOrm).where(CommentsOrm.id == comment_id))
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="comment not found")

    owner_user_id = comment.user_id

    await db.execute(delete(CommentsOrm).where(CommentsOrm.id == comment_id))
    await write_audit(
        db,
        actor_user_id=admin_user_id,
        action=ACTION_ADMIN_DELETE_COMMENT,
        target_type=TARGET_COMMENT,
        target_id=comment_id,
        metadata={"owner_user_id": owner_user_id},
    )
    await db.commit()


@router.post("/users/{target_user_id}/roles", status_code=status.HTTP_200_OK)
async def admin_assign_role(
    target_user_id: int,
    body: RoleAssignIn,
    db: db,
    admin_user_id: int = Depends(require_roles("admin")),
):
    await _require_other_user(db, admin_user_id, target_user_id)

    roles = await assign_role(db, target_user_id, body.role)
    await write_audit(
        db,
        actor_user_id=admin_user_id,
        action=ACTION_ROLE_ASSIGN,
        target_type=TARGET_USER,
        target_id=target_user_id,
        metadata={"role": body.role},
    )
    await db.commit()
    return {"user_id": target_user_id, "roles": sorted(roles)}


@router.delete("/users/{target_user_id}/roles/{role}", status_code=status.HTTP_200_OK)
async def admin_revoke_role(
    target_user_id: int,
    role: str,
    db: db,
    admin_user_id: int = Depends(require_roles("admin")),
):
    await _require_other_user(db, admin_user_id, target_user_id)

    roles = await revoke_role(db, target_user_id, role)
    await write_audit(
        db,
        actor_user_id=admin_user_id,
        action=ACTION_ROLE_REVOKE,
        target_type=TARGET_USER,
        target_id=target_user_id,
        metadata={"role": role},
    )
    await db.commit()
    return {"user_id": target_user_id, "roles": sorted(roles)}


@router.get("/audit", response_model=list[AuditLogOut])
async def admin_list_audit(
    db: db,
    _: int = Depends(require_roles("admin")),
    actor_user_id: int | None = None,
    action: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(AuditLogOrm)

    if actor_user_id is not None:
        query = query.where(AuditLogOrm.actor_user_id == actor_user_id)
    if action is not None:
        query = query.where(AuditLogOrm.action == action)
    if target_type is not None:
        query = query.where(AuditLogOrm.target_type == target_type)
    if target_id is not None:
        query = query.where(AuditLogOrm.target_id == target_id)
    if date_from is not None:
        query = query.where(AuditLogOrm.created_at >= date_from)
    if date_to is not None:
        query = query.where(AuditLogOrm.created_at <= date_to)

    rows = await db.scalars(
        query.order_by(desc(AuditLogOrm.created_at), desc(AuditLogOrm.id))
        .offset(offset)
        .limit(limit)
    )

    return rows.all()


@router.get("/copyright-reports", response_model=list[CopyrightReportOut])
async def admin_list_copyright_reports(
    db: db,
    _: int = Depends(require_roles("admin")),
    status_filter: str | None = Query(default=None, alias="status"),
    pin_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(CopyrightReportsOrm)
    if status_filter:
        query = query.where(CopyrightReportsOrm.status == status_filter)
    if pin_id is not None:
        query = query.where(CopyrightReportsOrm.pin_id == pin_id)
    rows = await db.scalars(
        query.order_by(desc(CopyrightReportsOrm.id)).offset(offset).limit(limit)
    )
    return list(rows.all())


@router.patch("/copyright-reports/{report_id}", response_model=CopyrightReportOut)
async def admin_patch_copyright_report(
    report_id: int,
    body: CopyrightReportAdminPatchIn,
    db: db,
    admin_user_id: int = Depends(require_roles("admin")),
):
    row = await db.get(CopyrightReportsOrm, report_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report_not_found")
    if row.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"report_{row.status}"
        )

    now = datetime.now(timezone.utc)
    unlisted_count = 0
    if body.status == "resolved":
        result = await db.execute(
            update(PinListingsOrm)
            .where(
                PinListingsOrm.pin_id == row.pin_id,
                PinListingsOrm.status == "listed",
            )
            .values(status="unlisted", updated_at=now)
        )
        unlisted_count = int(result.rowcount or 0)

    row = await db.scalar(
        update(CopyrightReportsOrm)
        .where(CopyrightReportsOrm.id == report_id)
        .values(
            status=body.status,
            admin_note=body.admin_note,
            resolved_by_user_id=admin_user_id,
            updated_at=now,
        )
        .returning(CopyrightReportsOrm)
    )
    action = (
        ACTION_COPYRIGHT_REPORT_RESOLVE
        if body.status == "resolved"
        else ACTION_COPYRIGHT_REPORT_DISMISS
    )
    meta = {"pin_id": row.pin_id, "status": body.status}
    if body.status == "resolved":
        meta["unlisted_count"] = unlisted_count
    await write_audit(
        db,
        actor_user_id=admin_user_id,
        action=action,
        target_type=TARGET_COPYRIGHT_REPORT,
        target_id=report_id,
        metadata=meta,
    )
    await db.commit()
    return row


@router.get(
    "/marketplace/payment-methods",
    response_model=list[AdminPaymentMethodOut],
)
async def admin_list_payment_methods(
    db: db,
    _: int = Depends(require_roles("admin")),
    verification_status: str | None = Query(
        default="unverified",
        description="unverified | verified | omit/all for every status",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    stmt = (
        select(SellerPaymentMethodsOrm, UsersOrm.username)
        .join(UsersOrm, UsersOrm.id == SellerPaymentMethodsOrm.user_id)
        .order_by(desc(SellerPaymentMethodsOrm.id))
        .offset(offset)
        .limit(limit)
    )
    status_filter = (verification_status or "").strip().lower()
    if status_filter in ("unverified", "verified"):
        stmt = stmt.where(SellerPaymentMethodsOrm.verification_status == status_filter)
    # "all" or anything else → no status filter
    rows = (await db.execute(stmt)).all()
    out: list[AdminPaymentMethodOut] = []
    for method, username in rows:
        out.append(
            AdminPaymentMethodOut(
                id=method.id,
                user_id=method.user_id,
                username=username,
                method_type=method.method_type,
                display_name=method.display_name,
                account_identifier=method.account_identifier,
                bank_name=method.bank_name,
                bank_code=method.bank_code,
                account_holder=method.account_holder,
                is_active=method.is_active,
                is_primary=method.is_primary,
                verification_status=method.verification_status,
                verified_at=method.verified_at,
                verified_by=method.verified_by,
                created_at=method.created_at,
            )
        )
    return out


@router.patch(
    "/marketplace/payment-methods/{method_id}",
    response_model=PaymentMethodOut,
)
async def admin_verify_payment_method(
    method_id: int,
    body: AdminPaymentMethodVerifyIn,
    db: db,
    admin_user_id: int = Depends(require_roles("admin")),
):
    row = await set_method_verification(
        db,
        method_id,
        verification_status=body.verification_status,
        verified_by=f"admin:{admin_user_id}",
    )
    await write_audit(
        db,
        actor_user_id=admin_user_id,
        action=ACTION_PAYMENT_METHOD_VERIFY,
        target_type=TARGET_PAYMENT_METHOD,
        target_id=method_id,
        metadata={
            "verification_status": body.verification_status,
            "user_id": row.user_id,
        },
    )
    await db.commit()
    return row


def _admin_payout_out(o: PinOrdersOrm) -> AdminPayoutOut:
    return AdminPayoutOut(
        order_id=o.id,
        pin_id=o.pin_id,
        seller_user_id=o.seller_user_id,
        buyer_user_id=o.buyer_user_id,
        paid_at=o.paid_at,
        currency=o.currency,
        price_minor=o.price_minor,
        seller_net_minor=o.seller_net_minor,
        payout_amount_vnd=o.payout_amount_vnd,
        payout_status=o.payout_status,
        payout_method_type=o.payout_method_type,
        payout_display_name=o.payout_display_name,
        payout_account_identifier=o.payout_account_identifier,
        payout_bank_name=o.payout_bank_name,
        payout_bank_code=o.payout_bank_code,
        payout_account_holder=o.payout_account_holder,
        payout_marked_at=o.payout_marked_at,
        payout_note=o.payout_note,
    )


@router.get("/marketplace/payouts/pending", response_model=list[AdminPayoutOut])
async def admin_list_pending_payouts(
    db: db,
    _: int = Depends(require_roles("admin")),
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Queue of paid orders awaiting seller disbursement.
    Provider is configured via MP_PAYOUT_PROVIDER (manual|stub; open_api disabled).
    """
    rows = await db.scalars(
        select(PinOrdersOrm)
        .where(
            PinOrdersOrm.status == "paid",
            PinOrdersOrm.payout_status.in_(("pending", "failed")),
        )
        .order_by(PinOrdersOrm.paid_at.asc().nulls_last(), PinOrdersOrm.id.asc())
        .limit(limit)
    )
    return [_admin_payout_out(o) for o in rows.all()]


@router.post(
    "/marketplace/payouts/{order_id}/execute",
    response_model=AdminPayoutOut,
)
async def admin_execute_payout(
    order_id: int,
    body: AdminPayoutExecuteIn,
    db: db,
    admin_user_id: int = Depends(require_roles("admin")),
):
    order = await execute_order_payout(
        db,
        order_id=order_id,
        actor_user_id=admin_user_id,
        force_fail=body.force_fail,
        note=body.note,
    )
    return _admin_payout_out(order)


@router.post(
    "/marketplace/payouts/{order_id}/mark-paid",
    response_model=AdminPayoutOut,
)
async def admin_mark_payout_paid(
    order_id: int,
    body: AdminPayoutMarkIn,
    db: db,
    admin_user_id: int = Depends(require_roles("admin")),
):
    order = await mark_payout_paid_manual(
        db,
        order_id=order_id,
        actor_user_id=admin_user_id,
        note=body.note,
    )
    return _admin_payout_out(order)
