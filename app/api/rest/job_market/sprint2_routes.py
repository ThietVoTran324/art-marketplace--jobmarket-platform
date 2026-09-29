"""JobMarket Sprint2 — KYC, company profile, admin decide."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import uuid

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy import delete, func, select

from app.api.rest.audit import (
    ACTION_KYC_APPROVE,
    ACTION_KYC_NEED_MORE_INFO,
    ACTION_KYC_REJECT,
    ACTION_KYC_SUBMIT,
    ACTION_ROLE_ASSIGN,
    TARGET_COMPANY,
    TARGET_KYC_REQUEST,
    TARGET_USER,
    write_audit,
)
from app.api.rest.dependencies import db, require_roles, user_id
from app.api.rest.ownership import assert_company_owner, assert_kyc_request_owner
from app.api.rest.roles import assign_role, get_user_roles
from app.api.rest.utils import (
    create_url_safe_token,
    decode_url_safe_token,
    delete_file,
    save_file_bytes,
)
from app.celery.tasks import send_email
from app.config import settings
from app.postgresql.models import (
    CompaniesOrm,
    CompanyBranchesOrm,
    CompanyVerificationDocumentsOrm,
    CompanyVerificationRequestsOrm,
    UsersOrm,
)

from .constants import (
    DEFAULT_TERMS_VERSION,
    ENGLISH_LANGUAGE,
    KYC_ALLOWED_CONTENT_TYPES,
    KYC_ALLOWED_EXTENSIONS,
    KYC_DOC_TYPES,
    KYC_MAX_BYTES,
    KYC_MAX_FILES_PER_REQUEST,
    KYC_MAX_FILES_PER_TYPE,
    SUPERSEDED_REJECTION_REASON,
)
from app.api.rest.role_gates import assert_can_submit_hiring_kyc
from .helpers import (
    collect_name_domain_warnings,
    default_authority,
    looks_like_encrypted_pdf,
    normalize_registration_number,
    resolve_account_kind,
)
from .schemas import (
    AdminNoteBody,
    AdminRejectBody,
    BranchCreate,
    BranchOut,
    BranchUpdate,
    CompanyOut,
    CompanyPublicOut,
    CompanyUpdate,
    HiringRightsRequestCreate,
    HiringRightsRequestOut,
    KycDocumentOut,
)

router = APIRouter()
AdminUserId = Annotated[int, Depends(require_roles("admin"))]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_owned_active_company(db, user_id: int) -> CompaniesOrm | None:
    return await db.scalar(
        select(CompaniesOrm).where(
            CompaniesOrm.owner_user_id == user_id,
            CompaniesOrm.status == "active",
        )
    )


async def _get_owned_company(db, user_id: int) -> CompaniesOrm | None:
    """Owner company when active or suspended (read / non-JD-mutate)."""
    return await db.scalar(
        select(CompaniesOrm).where(
            CompaniesOrm.owner_user_id == user_id,
            CompaniesOrm.status.in_(("active", "suspended")),
        )
    )


async def _require_verified_email(user: UsersOrm) -> str:
    if user.email is None or not str(user.email).strip():
        raise HTTPException(status_code=400, detail="email_required")
    if not user.verified:
        raise HTTPException(status_code=400, detail="email_not_verified")
    return str(user.email).strip()


def _request_out(row: CompanyVerificationRequestsOrm, warnings=None) -> HiringRightsRequestOut:
    out = HiringRightsRequestOut.model_validate(row)
    if warnings:
        out.warnings = warnings
    return out


def _company_out(row: CompaniesOrm, warnings=None) -> CompanyOut:
    out = CompanyOut.model_validate(row)
    if warnings:
        out.warnings = warnings
    return out


async def _send_confirm_email(user: UsersOrm, req: CompanyVerificationRequestsOrm) -> None:
    token = create_url_safe_token(
        {"request_id": req.id, "user_id": req.requester_user_id},
        expiration=86400,
    )
    link = f"{settings.API_DOMAIN}/job-market/kyc/confirm-email/{token}"
    send_email.delay(
        [req.company_email],
        "Confirm company email for hiring rights",
        {"username": user.username, "link": link},
        "mail_company_email_confirm.html",
    )


# ---- KYC me ----


@router.get("/me/hiring-rights-requests", response_model=list[HiringRightsRequestOut])
async def list_my_hiring_rights_requests(db: db, user_id: user_id):
    rows = (
        await db.scalars(
            select(CompanyVerificationRequestsOrm)
            .where(CompanyVerificationRequestsOrm.requester_user_id == user_id)
            .order_by(CompanyVerificationRequestsOrm.id.desc())
        )
    ).all()
    return rows


@router.get("/me/hiring-rights-requests/{request_id}", response_model=HiringRightsRequestOut)
async def get_my_hiring_rights_request(request_id: int, db: db, user_id: user_id):
    return await assert_kyc_request_owner(db, request_id, user_id)


@router.post(
    "/me/hiring-rights-requests",
    response_model=HiringRightsRequestOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_hiring_rights_request(
    body: HiringRightsRequestCreate,
    request: Request,
    db: db,
    user_id: user_id,
):
    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    account_email = await _require_verified_email(user)
    await assert_can_submit_hiring_kyc(db, user_id)

    if body.company_email.strip().lower() != account_email.lower():
        raise HTTPException(
            status_code=400,
            detail="company_email_must_match_account_email",
        )

    authority = default_authority(body.registration_authority)
    normalized = normalize_registration_number(body.registration_number_raw)
    if not normalized:
        raise HTTPException(status_code=400, detail="invalid_registration_number")

    existing = await db.scalar(
        select(CompaniesOrm).where(
            CompaniesOrm.registration_country == body.registration_country.strip(),
            CompaniesOrm.registration_authority == authority,
            CompaniesOrm.registration_type == body.registration_type.strip(),
            CompaniesOrm.registration_number_normalized == normalized,
        )
    )

    if existing is not None:
        if existing.status == "active":
            raise HTTPException(
                status_code=409,
                detail="company_already_verified_contact_support",
            )
        if existing.status in ("suspended", "soft_deleted"):
            raise HTTPException(
                status_code=409,
                detail="company_restricted_contact_support",
            )
        company = existing
        if company.status == "rejected":
            company.status = "pending_verification"
            company.updated_at = _now()
    else:
        company = CompaniesOrm(
            display_name=body.display_name.strip(),
            description=body.description,
            industry=body.industry,
            size_min=body.size_min,
            size_max=body.size_max,
            website=body.website,
            domain=body.domain,
            registration_country=body.registration_country.strip(),
            registration_authority=authority,
            registration_type=body.registration_type.strip(),
            registration_number_raw=body.registration_number_raw.strip(),
            registration_number_normalized=normalized,
            tax_id=body.tax_id,
            vat_number=body.vat_number,
            status="pending_verification",
        )
        db.add(company)
        await db.flush()

        if body.address_line:
            db.add(
                CompanyBranchesOrm(
                    company_id=company.id,
                    address_line=body.address_line.strip(),
                    city=body.city,
                    country=body.branch_country or body.registration_country.strip(),
                    is_primary=True,
                )
            )

    # pending_verification: reuse company, no spawn
    client_host = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    req_row = CompanyVerificationRequestsOrm(
        company_id=company.id,
        requester_user_id=user_id,
        status="pending",
        signer_full_name=body.signer_full_name.strip(),
        signed_at=_now(),
        signer_ip=client_host,
        signer_user_agent=(ua[:400] if ua else None),
        terms_version=body.terms_version or DEFAULT_TERMS_VERSION,
        company_email=account_email,
        primary_document_language=body.primary_document_language.strip().lower(),
    )
    db.add(req_row)
    await db.flush()

    warnings = await collect_name_domain_warnings(
        db, company.display_name, company.domain, exclude_company_id=company.id
    )

    await write_audit(
        db,
        actor_user_id=user_id,
        action=ACTION_KYC_SUBMIT,
        target_type=TARGET_KYC_REQUEST,
        target_id=req_row.id,
        metadata={"company_id": company.id},
    )
    await db.commit()
    await db.refresh(req_row)

    try:
        await _send_confirm_email(user, req_row)
    except Exception:
        # Mail failures should not roll back KYC submit; smoke can confirm via SQL.
        pass

    return _request_out(req_row, warnings)


@router.post(
    "/me/hiring-rights-requests/{request_id}/resend-confirm",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def resend_company_email_confirm(request_id: int, db: db, user_id: user_id):
    req_row = await assert_kyc_request_owner(db, request_id, user_id)
    if req_row.company_email_confirmed_at is not None:
        raise HTTPException(status_code=400, detail="already_confirmed")
    if req_row.status not in ("pending", "need_more_info"):
        raise HTTPException(status_code=400, detail="request_not_open")
    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    await _send_confirm_email(user, req_row)


@router.get(
    "/me/hiring-rights-requests/{request_id}/documents",
    response_model=list[KycDocumentOut],
)
async def list_my_kyc_documents(request_id: int, db: db, user_id: user_id):
    await assert_kyc_request_owner(db, request_id, user_id)
    return (
        await db.scalars(
            select(CompanyVerificationDocumentsOrm)
            .where(CompanyVerificationDocumentsOrm.request_id == request_id)
            .order_by(CompanyVerificationDocumentsOrm.id.asc())
        )
    ).all()


@router.post(
    "/me/hiring-rights-requests/{request_id}/documents",
    response_model=KycDocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_my_kyc_document(
    request_id: int,
    db: db,
    user_id: user_id,
    doc_type: Annotated[str, Form()],
    file: UploadFile = File(...),
):
    req_row = await assert_kyc_request_owner(db, request_id, user_id)
    if req_row.status not in ("pending", "need_more_info"):
        raise HTTPException(status_code=400, detail="request_not_open")
    if doc_type not in KYC_DOC_TYPES:
        raise HTTPException(status_code=422, detail="invalid_doc_type")

    total = await db.scalar(
        select(func.count())
        .select_from(CompanyVerificationDocumentsOrm)
        .where(CompanyVerificationDocumentsOrm.request_id == request_id)
    )
    if total is not None and total >= KYC_MAX_FILES_PER_REQUEST:
        raise HTTPException(status_code=400, detail="kyc_doc_quota_exceeded")

    type_count = await db.scalar(
        select(func.count())
        .select_from(CompanyVerificationDocumentsOrm)
        .where(
            CompanyVerificationDocumentsOrm.request_id == request_id,
            CompanyVerificationDocumentsOrm.doc_type == doc_type,
        )
    )
    if type_count is not None and type_count >= KYC_MAX_FILES_PER_TYPE:
        raise HTTPException(status_code=400, detail="kyc_doc_type_quota_exceeded")

    content_type = file.content_type or ""
    if content_type not in KYC_ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file type. Allowed: pdf, jpg, jpeg, png",
        )

    original = file.filename or "doc"
    ext = Path(original).suffix.lower()
    if ext not in KYC_ALLOWED_EXTENSIONS:
        ext = KYC_ALLOWED_CONTENT_TYPES[content_type]
    if ext == ".jpeg":
        ext = ".jpg"

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")
    if len(raw) > KYC_MAX_BYTES:
        raise HTTPException(status_code=400, detail="kyc_doc_too_large")
    if content_type == "application/pdf" and looks_like_encrypted_pdf(raw):
        raise HTTPException(status_code=400, detail="password_pdf_not_allowed")

    filename = f"{uuid.uuid4()}{ext}"
    media_root = Path(settings.MEDIA_PATH)
    kyc_dir = media_root / "kyc" / str(request_id)
    kyc_dir.mkdir(parents=True, exist_ok=True)
    full_path = kyc_dir / filename
    await save_file_bytes(raw, str(full_path))

    row = CompanyVerificationDocumentsOrm(
        request_id=request_id,
        doc_type=doc_type,
        original_filename=Path(original).name[:255],
        stored_name=f"kyc/{request_id}/{filename}",
        content_type=content_type,
        size_bytes=len(raw),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete(
    "/me/hiring-rights-requests/{request_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_my_kyc_document(
    request_id: int, doc_id: int, db: db, user_id: user_id
):
    req = await assert_kyc_request_owner(db, request_id, user_id)
    if req.status not in ("pending", "need_more_info"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="request_not_open",
        )
    row = await db.scalar(
        select(CompanyVerificationDocumentsOrm).where(
            CompanyVerificationDocumentsOrm.id == doc_id,
            CompanyVerificationDocumentsOrm.request_id == request_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    await delete_file(str(Path(settings.MEDIA_PATH) / row.stored_name))
    await db.execute(
        delete(CompanyVerificationDocumentsOrm).where(
            CompanyVerificationDocumentsOrm.id == doc_id
        )
    )
    await db.commit()


@router.get("/me/hiring-rights-requests/{request_id}/documents/{doc_id}/file")
async def download_my_kyc_document(
    request_id: int, doc_id: int, db: db, user_id: user_id
):
    await assert_kyc_request_owner(db, request_id, user_id)
    row = await db.scalar(
        select(CompanyVerificationDocumentsOrm).where(
            CompanyVerificationDocumentsOrm.id == doc_id,
            CompanyVerificationDocumentsOrm.request_id == request_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    path = Path(settings.MEDIA_PATH) / row.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(
        path, media_type=row.content_type, filename=row.original_filename
    )


# ---- Confirm email ----


@router.get("/kyc/confirm-email/{token}")
async def confirm_company_email(token: str, db: db):
    data = decode_url_safe_token(token, max_age=86400)
    request_id = data.get("request_id")
    requester_id = data.get("user_id")
    if request_id is None or requester_id is None:
        raise HTTPException(status_code=400, detail="Invalid token")

    req_row = await db.scalar(
        select(CompanyVerificationRequestsOrm).where(
            CompanyVerificationRequestsOrm.id == int(request_id),
            CompanyVerificationRequestsOrm.requester_user_id == int(requester_id),
        )
    )
    if req_row is None:
        raise HTTPException(status_code=404, detail="kyc request not found")

    if req_row.company_email_confirmed_at is None:
        req_row.company_email_confirmed_at = _now()
        req_row.updated_at = _now()
        await db.commit()

    frontend = getattr(settings, "FRONTEND_DOMAIN", None) or ""
    if frontend:
        return RedirectResponse(
            url=f"{frontend.rstrip('/')}/settings?kyc_confirmed=1",
            status_code=302,
        )
    return JSONResponse({"status": "OK", "request_id": req_row.id})


# ---- Admin ----


@router.get(
    "/admin/hiring-rights-requests",
    response_model=list[HiringRightsRequestOut],
)
async def admin_list_hiring_rights_requests(
    db: db,
    admin_user_id: AdminUserId,
    status_filter: str | None = Query(default=None, alias="status"),
    registration_number_normalized: str | None = None,
    registration_country: str | None = None,
):
    stmt = select(CompanyVerificationRequestsOrm)
    if status_filter:
        if status_filter not in ("pending", "need_more_info", "approved", "rejected"):
            raise HTTPException(status_code=422, detail="invalid status")
        stmt = stmt.where(CompanyVerificationRequestsOrm.status == status_filter)
    if registration_number_normalized or registration_country:
        stmt = stmt.join(
            CompaniesOrm,
            CompaniesOrm.id == CompanyVerificationRequestsOrm.company_id,
        )
        if registration_number_normalized:
            stmt = stmt.where(
                CompaniesOrm.registration_number_normalized
                == normalize_registration_number(registration_number_normalized)
            )
        if registration_country:
            stmt = stmt.where(
                CompaniesOrm.registration_country == registration_country.strip()
            )
    stmt = stmt.order_by(CompanyVerificationRequestsOrm.id.asc())
    return (await db.scalars(stmt)).all()


async def _assert_docs_ready_for_approve(
    db, req_row: CompanyVerificationRequestsOrm
) -> None:
    docs = (
        await db.scalars(
            select(CompanyVerificationDocumentsOrm).where(
                CompanyVerificationDocumentsOrm.request_id == req_row.id
            )
        )
    ).all()
    types = {d.doc_type for d in docs}
    if "business_registration_document" not in types:
        raise HTTPException(
            status_code=400, detail="business_registration_document_required"
        )
    lang = (req_row.primary_document_language or "").lower()
    if lang not in (ENGLISH_LANGUAGE, "eng", "english") and "document_translation" not in types:
        raise HTTPException(status_code=400, detail="document_translation_required")


@router.post(
    "/admin/hiring-rights-requests/{request_id}/approve",
    response_model=HiringRightsRequestOut,
)
async def admin_approve_hiring_rights(
    request_id: int, db: db, admin_user_id: AdminUserId
):
    req_row = await db.scalar(
        select(CompanyVerificationRequestsOrm).where(
            CompanyVerificationRequestsOrm.id == request_id
        )
    )
    if req_row is None:
        raise HTTPException(status_code=404, detail="kyc request not found")
    if req_row.status not in ("pending", "need_more_info"):
        raise HTTPException(status_code=400, detail="request_not_open")
    if req_row.company_email_confirmed_at is None:
        raise HTTPException(status_code=400, detail="company_email_not_confirmed")

    await _assert_docs_ready_for_approve(db, req_row)

    company = await db.scalar(
        select(CompaniesOrm).where(CompaniesOrm.id == req_row.company_id)
    )
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    if company.status == "active" and company.owner_user_id not in (
        None,
        req_row.requester_user_id,
    ):
        raise HTTPException(status_code=409, detail="company_already_verified_contact_support")

    existing_owner = await _get_owned_active_company(db, req_row.requester_user_id)
    if existing_owner is not None and existing_owner.id != company.id:
        raise HTTPException(status_code=400, detail="already_has_hiring_rights")

    now = _now()
    req_row.status = "approved"
    req_row.updated_at = now

    company.status = "active"
    company.owner_user_id = req_row.requester_user_id
    company.verified_at = now
    company.updated_at = now

    siblings = (
        await db.scalars(
            select(CompanyVerificationRequestsOrm).where(
                CompanyVerificationRequestsOrm.company_id == company.id,
                CompanyVerificationRequestsOrm.id != req_row.id,
                CompanyVerificationRequestsOrm.status.in_(("pending", "need_more_info")),
            )
        )
    ).all()
    for sibling in siblings:
        sibling.status = "rejected"
        sibling.rejection_reason = SUPERSEDED_REJECTION_REASON
        sibling.updated_at = now
        await write_audit(
            db,
            actor_user_id=admin_user_id,
            action=ACTION_KYC_REJECT,
            target_type=TARGET_KYC_REQUEST,
            target_id=sibling.id,
            metadata={"reason": SUPERSEDED_REJECTION_REASON, "approved_request_id": req_row.id},
        )

    await assign_role(db, req_row.requester_user_id, "employer")
    await write_audit(
        db,
        actor_user_id=admin_user_id,
        action=ACTION_KYC_APPROVE,
        target_type=TARGET_KYC_REQUEST,
        target_id=req_row.id,
        metadata={"company_id": company.id, "requester_user_id": req_row.requester_user_id},
    )
    await write_audit(
        db,
        actor_user_id=admin_user_id,
        action=ACTION_ROLE_ASSIGN,
        target_type=TARGET_USER,
        target_id=req_row.requester_user_id,
        metadata={"role": "employer", "via": "kyc_approve"},
    )
    await db.commit()
    await db.refresh(req_row)
    return req_row


@router.post(
    "/admin/hiring-rights-requests/{request_id}/need-more-info",
    response_model=HiringRightsRequestOut,
)
async def admin_need_more_info(
    request_id: int, body: AdminNoteBody, db: db, admin_user_id: AdminUserId
):
    req_row = await db.scalar(
        select(CompanyVerificationRequestsOrm).where(
            CompanyVerificationRequestsOrm.id == request_id
        )
    )
    if req_row is None:
        raise HTTPException(status_code=404, detail="kyc request not found")
    if req_row.status not in ("pending", "need_more_info"):
        raise HTTPException(status_code=400, detail="request_not_open")

    req_row.status = "need_more_info"
    req_row.admin_note = body.note
    req_row.updated_at = _now()
    await write_audit(
        db,
        actor_user_id=admin_user_id,
        action=ACTION_KYC_NEED_MORE_INFO,
        target_type=TARGET_KYC_REQUEST,
        target_id=req_row.id,
        metadata={"note": body.note},
    )
    await db.commit()
    await db.refresh(req_row)
    return req_row


@router.post(
    "/admin/hiring-rights-requests/{request_id}/reject",
    response_model=HiringRightsRequestOut,
)
async def admin_reject_hiring_rights(
    request_id: int, body: AdminRejectBody, db: db, admin_user_id: AdminUserId
):
    req_row = await db.scalar(
        select(CompanyVerificationRequestsOrm).where(
            CompanyVerificationRequestsOrm.id == request_id
        )
    )
    if req_row is None:
        raise HTTPException(status_code=404, detail="kyc request not found")
    if req_row.status not in ("pending", "need_more_info"):
        raise HTTPException(status_code=400, detail="request_not_open")

    req_row.status = "rejected"
    req_row.rejection_reason = body.reason
    req_row.updated_at = _now()

    company = await db.scalar(
        select(CompaniesOrm).where(CompaniesOrm.id == req_row.company_id)
    )
    # If no other open requests, mark company rejected (reuse later).
    if company is not None and company.status == "pending_verification":
        open_others = await db.scalar(
            select(func.count())
            .select_from(CompanyVerificationRequestsOrm)
            .where(
                CompanyVerificationRequestsOrm.company_id == company.id,
                CompanyVerificationRequestsOrm.id != req_row.id,
                CompanyVerificationRequestsOrm.status.in_(("pending", "need_more_info")),
            )
        )
        if not open_others:
            company.status = "rejected"
            company.updated_at = _now()

    await write_audit(
        db,
        actor_user_id=admin_user_id,
        action=ACTION_KYC_REJECT,
        target_type=TARGET_KYC_REQUEST,
        target_id=req_row.id,
        metadata={"reason": body.reason},
    )
    await db.commit()
    await db.refresh(req_row)
    return req_row


@router.get(
    "/admin/hiring-rights-requests/{request_id}/documents",
    response_model=list[KycDocumentOut],
)
async def admin_list_kyc_documents(
    request_id: int, db: db, admin_user_id: AdminUserId
):
    _ = admin_user_id
    req_row = await db.scalar(
        select(CompanyVerificationRequestsOrm).where(
            CompanyVerificationRequestsOrm.id == request_id
        )
    )
    if req_row is None:
        raise HTTPException(status_code=404, detail="kyc request not found")
    return (
        await db.scalars(
            select(CompanyVerificationDocumentsOrm)
            .where(CompanyVerificationDocumentsOrm.request_id == request_id)
            .order_by(CompanyVerificationDocumentsOrm.id.asc())
        )
    ).all()


@router.get("/admin/hiring-rights-requests/{request_id}/documents/{doc_id}/file")
async def admin_download_kyc_document(
    request_id: int, doc_id: int, db: db, admin_user_id: AdminUserId
):
    row = await db.scalar(
        select(CompanyVerificationDocumentsOrm).where(
            CompanyVerificationDocumentsOrm.id == doc_id,
            CompanyVerificationDocumentsOrm.request_id == request_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    path = Path(settings.MEDIA_PATH) / row.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(
        path, media_type=row.content_type, filename=row.original_filename
    )


# ---- Company profile ----


@router.get(
    "/companies/{company_id}",
    response_model=CompanyOut | CompanyPublicOut,
)
async def get_company(company_id: int, db: db, user_id: user_id):
    row = await db.scalar(select(CompaniesOrm).where(CompaniesOrm.id == company_id))
    if row is None:
        raise HTTPException(status_code=404, detail="company not found")
    if row.status == "active" or (
        row.status == "suspended" and row.owner_user_id == user_id
    ):
        if row.owner_user_id == user_id:
            return CompanyOut.model_validate(row)
        return CompanyPublicOut.model_validate(row)
    raise HTTPException(status_code=404, detail="company not found")


@router.get("/companies/{company_id}/branches", response_model=list[BranchOut])
async def list_company_branches(company_id: int, db: db, user_id: user_id):
    company = await db.scalar(select(CompaniesOrm).where(CompaniesOrm.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    if company.status == "active" or (
        company.status == "suspended" and company.owner_user_id == user_id
    ):
        return (
            await db.scalars(
                select(CompanyBranchesOrm)
                .where(CompanyBranchesOrm.company_id == company_id)
                .order_by(CompanyBranchesOrm.id.asc())
            )
        ).all()
    raise HTTPException(status_code=404, detail="company not found")


@router.patch("/me/company", response_model=CompanyOut)
async def update_my_company(body: CompanyUpdate, db: db, user_id: user_id):
    roles = await get_user_roles(db, user_id)
    if "employer" not in roles:
        raise HTTPException(status_code=403, detail="hiring_rights_required")
    company = await _get_owned_company(db, user_id)
    if company is None:
        raise HTTPException(status_code=403, detail="not company owner")

    data = body.model_dump(exclude_none=True)
    size_min = data.get("size_min", company.size_min)
    size_max = data.get("size_max", company.size_max)
    if size_min is not None and size_max is not None and size_max < size_min:
        raise HTTPException(status_code=422, detail="size_max must be >= size_min")

    for key, value in data.items():
        setattr(company, key, value)
    company.updated_at = _now()

    warnings = await collect_name_domain_warnings(
        db,
        company.display_name,
        company.domain,
        exclude_company_id=company.id,
    )
    await db.commit()
    await db.refresh(company)
    return _company_out(company, warnings)


@router.post(
    "/me/company/branches",
    response_model=BranchOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_my_company_branch(body: BranchCreate, db: db, user_id: user_id):
    roles = await get_user_roles(db, user_id)
    if "employer" not in roles:
        raise HTTPException(status_code=403, detail="hiring_rights_required")
    company = await _get_owned_active_company(db, user_id)
    if company is None:
        raise HTTPException(status_code=403, detail="not company owner")
    await assert_company_owner(db, company.id, user_id)

    row = CompanyBranchesOrm(
        company_id=company.id,
        label=body.label,
        address_line=body.address_line,
        city=body.city,
        country=body.country,
        is_primary=body.is_primary,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.patch("/me/company/branches/{branch_id}", response_model=BranchOut)
async def update_my_company_branch(
    branch_id: int, body: BranchUpdate, db: db, user_id: user_id
):
    roles = await get_user_roles(db, user_id)
    if "employer" not in roles:
        raise HTTPException(status_code=403, detail="hiring_rights_required")
    company = await _get_owned_active_company(db, user_id)
    if company is None:
        raise HTTPException(status_code=403, detail="not company owner")
    row = await db.scalar(
        select(CompanyBranchesOrm).where(
            CompanyBranchesOrm.id == branch_id,
            CompanyBranchesOrm.company_id == company.id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="branch not found")
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(row, key, value)
    row.updated_at = _now()
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/me/company/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_company_branch(branch_id: int, db: db, user_id: user_id):
    roles = await get_user_roles(db, user_id)
    if "employer" not in roles:
        raise HTTPException(status_code=403, detail="hiring_rights_required")
    company = await _get_owned_active_company(db, user_id)
    if company is None:
        raise HTTPException(status_code=403, detail="not company owner")
    row = await db.scalar(
        select(CompanyBranchesOrm).where(
            CompanyBranchesOrm.id == branch_id,
            CompanyBranchesOrm.company_id == company.id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="branch not found")
    await db.execute(
        delete(CompanyBranchesOrm).where(CompanyBranchesOrm.id == branch_id)
    )
    await db.commit()
