"""JobMarket Sprint4 — apply, applications, view-CV, status."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.rest.dependencies import db, user_id
from app.api.rest.ownership import (
    assert_application_company_owner,
    assert_cv_owner,
    assert_job_post_company_owner,
)
from app.api.rest.utils import save_file_bytes
from app.config import settings
from app.postgresql.models import (
    CompaniesOrm,
    JobApplicationsOrm,
    JobPostsOrm,
    UserCvsOrm,
    UsersOrm,
)

from .constants import (
    APP_STATUS_PASSED,
    APP_STATUS_REJECTED,
    APP_STATUS_SUBMITTED,
    APP_STATUS_VIEWED,
    APP_TERMINAL,
    COVER_NOTE_MAX_LEN,
    CV_ALLOWED_CONTENT_TYPES,
    CV_ALLOWED_EXTENSIONS,
    CV_MAX_BYTES,
    CV_SOURCE_ONESHOT,
    CV_SOURCE_TAB,
    JOB_STATUS_ACTIVE,
)
from app.api.rest.job_market.helpers import resolve_account_kind
from app.api.rest.role_gates import assert_can_apply_to_job
from .notify import notify_applicant_status, notify_company_new_application
from .schemas import ApplicationCvViewOut, JobApplicationOut, MyApplicationBrief

router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _app_out(row: JobApplicationsOrm, username: str | None = None) -> JobApplicationOut:
    return JobApplicationOut(
        id=row.id,
        job_post_id=row.job_post_id,
        applicant_user_id=row.applicant_user_id,
        status=row.status,  # type: ignore[arg-type]
        cover_note=row.cover_note,
        has_cover_file=bool(row.cover_stored_name),
        cv_source=row.cv_source,  # type: ignore[arg-type]
        source_cv_id=row.source_cv_id,
        cv_original_filename=row.cv_original_filename,
        viewed_at=row.viewed_at,
        decided_at=row.decided_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        applicant_username=username,
    )


def _validate_doc_upload(content_type: str, filename: str, size: int) -> str:
    if content_type not in CV_ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Invalid file type. Allowed: pdf, doc, docx",
        )
    ext = Path(filename or "file").suffix.lower()
    if ext not in CV_ALLOWED_EXTENSIONS:
        ext = CV_ALLOWED_CONTENT_TYPES[content_type]
    if size > CV_MAX_BYTES:
        raise HTTPException(status_code=400, detail="file_too_large")
    if size <= 0:
        raise HTTPException(status_code=400, detail="empty file")
    return ext


async def _copy_cv_from_tab(
    db, *, user_id: int, cv_id: int, app_id: int
) -> tuple[str, str, str, int, int]:
    cv = await assert_cv_owner(db, cv_id, user_id)
    src = Path(settings.MEDIA_PATH) / cv.stored_name
    if not src.exists():
        raise HTTPException(status_code=404, detail="cv file not found")
    dest_rel = f"job_applications/{app_id}/cv{Path(cv.stored_name).suffix}"
    dest = Path(settings.MEDIA_PATH) / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return (
        cv.original_filename,
        dest_rel,
        cv.content_type,
        cv.size_bytes,
        cv.id,
    )


async def _maybe_mark_viewed(
    db, row: JobApplicationsOrm, *, owner_id: int, job: JobPostsOrm
) -> None:
    if row.status != APP_STATUS_SUBMITTED:
        return
    row.status = APP_STATUS_VIEWED
    row.viewed_at = _now()
    row.updated_at = _now()
    applicant = await db.scalar(
        select(UsersOrm).where(UsersOrm.id == row.applicant_user_id)
    )
    if applicant:
        await notify_applicant_status(
            db,
            applicant=applicant,
            owner_id=owner_id,
            job_id=job.id,
            application_id=row.id,
            job_title=job.title,
            status="viewed",
        )


@router.post(
    "/jobs/{job_post_id}/apply",
    response_model=JobApplicationOut,
    status_code=status.HTTP_201_CREATED,
)
async def apply_to_job(
    job_post_id: int,
    db: db,
    user_id: user_id,
    cover_note: str | None = Form(default=None),
    cv_id: int | None = Form(default=None),
    cover_file: UploadFile | None = File(default=None),
    cv: UploadFile | None = File(default=None),
):
    await assert_can_apply_to_job(db, user_id)

    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    if user.email is None or not str(user.email).strip() or not user.verified:
        raise HTTPException(status_code=400, detail="email_required")

    job = await db.scalar(select(JobPostsOrm).where(JobPostsOrm.id == job_post_id))
    if job is None:
        raise HTTPException(status_code=404, detail="job post not found")
    if job.status != JOB_STATUS_ACTIVE:
        raise HTTPException(status_code=400, detail="job_closed")
    expires_at = job.expires_at
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="job_expired")
    company = await db.scalar(select(CompaniesOrm).where(CompaniesOrm.id == job.company_id))
    if company is None or company.status != "active":
        raise HTTPException(status_code=400, detail="company_not_active")

    prior = await db.scalar(
        select(JobApplicationsOrm)
        .where(
            JobApplicationsOrm.applicant_user_id == user_id,
            JobApplicationsOrm.job_post_id == job_post_id,
            JobApplicationsOrm.hiring_cycle == job.hiring_cycle,
        )
        .limit(1)
    )
    if prior is not None:
        raise HTTPException(status_code=409, detail="already_applied")

    has_cv_id = cv_id is not None
    has_cv_file = cv is not None and cv.filename
    if has_cv_id == bool(has_cv_file):
        raise HTTPException(
            status_code=422,
            detail="provide exactly one of cv_id or cv file",
        )

    note = cover_note.strip() if cover_note and cover_note.strip() else None
    if note and len(note) > COVER_NOTE_MAX_LEN:
        raise HTTPException(status_code=422, detail="cover_note too long")

    row = JobApplicationsOrm(
        job_post_id=job_post_id,
        applicant_user_id=user_id,
        hiring_cycle=job.hiring_cycle,
        status=APP_STATUS_SUBMITTED,
        cover_note=note,
        cv_source=CV_SOURCE_TAB if has_cv_id else CV_SOURCE_ONESHOT,
        cv_original_filename="pending",
        cv_stored_name="pending",
        cv_content_type="application/octet-stream",
        cv_size_bytes=0,
    )
    db.add(row)
    await db.flush()

    app_dir = Path(settings.MEDIA_PATH) / "job_applications" / str(row.id)
    app_dir.mkdir(parents=True, exist_ok=True)

    if has_cv_id:
        orig, stored, ctype, size, src_id = await _copy_cv_from_tab(
            db, user_id=user_id, cv_id=cv_id, app_id=row.id
        )
        row.cv_original_filename = orig
        row.cv_stored_name = stored
        row.cv_content_type = ctype
        row.cv_size_bytes = size
        row.source_cv_id = src_id
    else:
        raw = await cv.read()
        content_type = cv.content_type or ""
        ext = _validate_doc_upload(content_type, cv.filename or "cv", len(raw))
        stored_name = f"job_applications/{row.id}/cv{ext}"
        await save_file_bytes(raw, str(Path(settings.MEDIA_PATH) / stored_name))
        row.cv_original_filename = Path(cv.filename or f"cv{ext}").name[:255]
        row.cv_stored_name = stored_name
        row.cv_content_type = content_type
        row.cv_size_bytes = len(raw)
        row.source_cv_id = None

    if cover_file is not None and cover_file.filename:
        craw = await cover_file.read()
        cctype = cover_file.content_type or ""
        cext = _validate_doc_upload(cctype, cover_file.filename, len(craw))
        cstored = f"job_applications/{row.id}/cover{cext}"
        await save_file_bytes(craw, str(Path(settings.MEDIA_PATH) / cstored))
        row.cover_original_filename = Path(cover_file.filename).name[:255]
        row.cover_stored_name = cstored
        row.cover_content_type = cctype
        row.cover_size_bytes = len(craw)

    owner = await db.scalar(select(UsersOrm).where(UsersOrm.id == company.owner_user_id))
    if owner:
        await notify_company_new_application(
            db,
            owner=owner,
            applicant=user,
            job_id=job.id,
            application_id=row.id,
            job_title=job.title,
        )

    await db.commit()
    await db.refresh(row)
    return _app_out(row, username=user.username)


@router.get(
    "/me/job-posts/{job_post_id}/applications",
    response_model=list[JobApplicationOut],
)
async def list_job_applications(job_post_id: int, db: db, user_id: user_id):
    await assert_job_post_company_owner(db, job_post_id, user_id)
    rows = (
        await db.scalars(
            select(JobApplicationsOrm)
            .where(JobApplicationsOrm.job_post_id == job_post_id)
            .order_by(
                JobApplicationsOrm.created_at.desc(), JobApplicationsOrm.id.desc()
            )
        )
    ).all()
    out = []
    for row in rows:
        u = await db.scalar(select(UsersOrm).where(UsersOrm.id == row.applicant_user_id))
        out.append(_app_out(row, username=u.username if u else None))
    return out


@router.post(
    "/me/job-posts/{job_post_id}/applications/{application_id}/reject",
    response_model=JobApplicationOut,
)
async def reject_application(
    job_post_id: int, application_id: int, db: db, user_id: user_id
):
    return await _decide(job_post_id, application_id, db, user_id, APP_STATUS_REJECTED)


@router.post(
    "/me/job-posts/{job_post_id}/applications/{application_id}/pass",
    response_model=JobApplicationOut,
)
async def pass_application(
    job_post_id: int, application_id: int, db: db, user_id: user_id
):
    return await _decide(job_post_id, application_id, db, user_id, APP_STATUS_PASSED)


async def _decide(
    job_post_id: int,
    application_id: int,
    db,
    user_id: int,
    new_status: str,
) -> JobApplicationOut:
    job = await assert_job_post_company_owner(db, job_post_id, user_id)
    row = await db.scalar(
        select(JobApplicationsOrm).where(
            JobApplicationsOrm.id == application_id,
            JobApplicationsOrm.job_post_id == job_post_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="application not found")
    if row.status in APP_TERMINAL:
        raise HTTPException(status_code=409, detail="application_terminal")
    row.status = new_status
    row.decided_at = _now()
    row.updated_at = _now()
    applicant = await db.scalar(
        select(UsersOrm).where(UsersOrm.id == row.applicant_user_id)
    )
    if applicant:
        await notify_applicant_status(
            db,
            applicant=applicant,
            owner_id=user_id,
            job_id=job.id,
            application_id=row.id,
            job_title=job.title,
            status=new_status,
        )
    await db.commit()
    await db.refresh(row)
    return _app_out(row, username=applicant.username if applicant else None)


@router.get("/applications/{application_id}/cv-view", response_model=ApplicationCvViewOut)
async def application_cv_view(application_id: int, db: db, user_id: user_id):
    row = await assert_application_company_owner(db, application_id, user_id)
    job = await db.scalar(select(JobPostsOrm).where(JobPostsOrm.id == row.job_post_id))
    await _maybe_mark_viewed(db, row, owner_id=user_id, job=job)
    await db.commit()
    await db.refresh(row)
    applicant = await db.scalar(
        select(UsersOrm).where(UsersOrm.id == row.applicant_user_id)
    )
    return ApplicationCvViewOut(
        id=row.id,
        job_post_id=row.job_post_id,
        job_title=job.title if job else None,
        applicant_user_id=row.applicant_user_id,
        applicant_username=applicant.username if applicant else None,
        status=row.status,  # type: ignore[arg-type]
        cover_note=row.cover_note,
        has_cover_file=bool(row.cover_stored_name),
        cv_original_filename=row.cv_original_filename,
        cv_content_type=row.cv_content_type,
        viewed_at=row.viewed_at,
        decided_at=row.decided_at,
        created_at=row.created_at,
    )


@router.get("/applications/{application_id}/cv/file")
async def download_application_cv(application_id: int, db: db, user_id: user_id):
    row = await assert_application_company_owner(db, application_id, user_id)
    job = await db.scalar(select(JobPostsOrm).where(JobPostsOrm.id == row.job_post_id))
    await _maybe_mark_viewed(db, row, owner_id=user_id, job=job)
    await db.commit()
    path = Path(settings.MEDIA_PATH) / row.cv_stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(
        path, media_type=row.cv_content_type, filename=row.cv_original_filename
    )


@router.get("/applications/{application_id}/cover/file")
async def download_application_cover(application_id: int, db: db, user_id: user_id):
    row = await assert_application_company_owner(db, application_id, user_id)
    if not row.cover_stored_name:
        raise HTTPException(status_code=404, detail="cover not found")
    path = Path(settings.MEDIA_PATH) / row.cover_stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(
        path,
        media_type=row.cover_content_type or "application/octet-stream",
        filename=row.cover_original_filename or "cover",
    )
