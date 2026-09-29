"""Job Market notify helpers (email + in-app best-effort)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.celery.tasks import send_email
from app.config import settings
from app.logger import logger
from app.postgresql.models import UpdatesOrm, UsersOrm
from redis import asyncio as aioredis

from .constants import (
    UPDATE_TYPE_APPLICATION_PASSED,
    UPDATE_TYPE_APPLICATION_RECEIVED,
    UPDATE_TYPE_APPLICATION_REJECTED,
    UPDATE_TYPE_APPLICATION_VIEWED,
    UPDATE_TYPE_COMPANY_SUSPENDED,
    UPDATE_TYPE_COMPANY_UNSUSPENDED,
    UPDATE_TYPE_WORK_EXP_APPROVED,
    UPDATE_TYPE_WORK_EXP_PENDING,
    UPDATE_TYPE_WORK_EXP_REJECTED,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _publish_update(user_id: int, payload: dict) -> None:
    try:
        redis = aioredis.from_url(settings.REDIS_URL_CELERY_BROKER, decode_responses=True)
        await redis.publish(f"notifications:{user_id}", json.dumps(payload, default=str))
        await redis.aclose()
    except Exception as e:
        logger.error(f"redis publish update failed: {e}", exc_info=True)


async def create_in_app_update(
    db: AsyncSession,
    *,
    to_user_id: int,
    update_type: str,
    content: str,
    actor_user_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    try:
        row = UpdatesOrm(
            user_update_to_id=to_user_id,
            content=content[:100] if content else None,
            update_type=update_type,
            is_read=False,
            user_id=actor_user_id,
            meta=metadata,
        )
        db.add(row)
        await db.flush()
        payload = {
            "id": row.id,
            "content": row.content,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "is_read": row.is_read,
            "update_type": row.update_type,
            "user_id": row.user_id,
            "metadata": metadata,
        }
        await _publish_update(to_user_id, payload)
    except Exception as e:
        logger.error(f"in-app update failed: {e}", exc_info=True)


def _safe_email(recipients: list[str], subject: str, context: dict, template: str) -> None:
    try:
        emails = [e for e in recipients if e]
        if not emails:
            return
        send_email.delay(emails, subject, context, template)
    except Exception as e:
        logger.error(f"queue email failed: {e}", exc_info=True)


async def notify_company_new_application(
    db: AsyncSession,
    *,
    owner: UsersOrm,
    applicant: UsersOrm,
    job_id: int,
    application_id: int,
    job_title: str,
) -> None:
    meta = {
        "job_id": job_id,
        "application_id": application_id,
        "applicant_username": applicant.username,
    }
    await create_in_app_update(
        db,
        to_user_id=owner.id,
        update_type=UPDATE_TYPE_APPLICATION_RECEIVED,
        content=f"New apply: {job_title[:60]}",
        actor_user_id=applicant.id,
        metadata=meta,
    )
    fe = settings.FRONTEND_DOMAIN.rstrip("/")
    _safe_email(
        [str(owner.email)] if owner.email else [],
        f"New application ? {job_title}",
        {
            "job_title": job_title,
            "applicant_username": applicant.username,
            "profile_link": f"{fe}/user/{applicant.username}",
            "cv_link": f"{fe}/applications/{application_id}/cv",
            "home_link": fe,
        },
        "mail_job_application_received.html",
    )


async def notify_applicant_status(
    db: AsyncSession,
    *,
    applicant: UsersOrm,
    owner_id: int,
    job_id: int,
    application_id: int,
    job_title: str,
    status: str,
) -> None:
    type_map = {
        "viewed": UPDATE_TYPE_APPLICATION_VIEWED,
        "rejected": UPDATE_TYPE_APPLICATION_REJECTED,
        "passed": UPDATE_TYPE_APPLICATION_PASSED,
    }
    update_type = type_map.get(status)
    if not update_type:
        return
    meta = {"job_id": job_id, "application_id": application_id}
    await create_in_app_update(
        db,
        to_user_id=applicant.id,
        update_type=update_type,
        content=f"Application {status}: {job_title[:50]}",
        actor_user_id=owner_id,
        metadata=meta,
    )
    fe = settings.FRONTEND_DOMAIN.rstrip("/")
    _safe_email(
        [str(applicant.email)] if applicant.email else [],
        f"Application {status} ? {job_title}",
        {
            "job_title": job_title,
            "status": status,
            "job_link": f"{fe}/jobs/{job_id}",
            "home_link": fe,
        },
        "mail_job_application_status.html",
    )


async def notify_company_work_exp_pending(
    db: AsyncSession,
    *,
    owner: UsersOrm,
    artist: UsersOrm,
    work_exp_id: int,
    company_name: str,
) -> None:
    meta = {
        "work_exp_id": work_exp_id,
        "artist_username": artist.username,
        "tab": "experience",
    }
    await create_in_app_update(
        db,
        to_user_id=owner.id,
        update_type=UPDATE_TYPE_WORK_EXP_PENDING,
        content=f"Work exp pending: {artist.username}"[:100],
        actor_user_id=artist.id,
        metadata=meta,
    )
    fe = settings.FRONTEND_DOMAIN.rstrip("/")
    _safe_email(
        [str(owner.email)] if owner.email else [],
        f"Work experience to review - {company_name}",
        {
            "artist_username": artist.username,
            "company_name": company_name,
            "profile_link": f"{fe}/user/{artist.username}?tab=experience&workExpId={work_exp_id}",
            "home_link": fe,
        },
        "mail_work_exp_pending.html",
    )


async def notify_artist_work_exp_status(
    db: AsyncSession,
    *,
    artist: UsersOrm,
    owner_id: int,
    work_exp_id: int,
    status: str,
    company_name: str,
) -> None:
    update_type = (
        UPDATE_TYPE_WORK_EXP_APPROVED
        if status == "approved"
        else UPDATE_TYPE_WORK_EXP_REJECTED
    )
    meta = {"work_exp_id": work_exp_id, "tab": "experience", "artist_username": artist.username}
    await create_in_app_update(
        db,
        to_user_id=artist.id,
        update_type=update_type,
        content=f"Work exp {status}: {company_name}"[:100],
        actor_user_id=owner_id,
        metadata=meta,
    )
    fe = settings.FRONTEND_DOMAIN.rstrip("/")
    _safe_email(
        [str(artist.email)] if artist.email else [],
        f"Work experience {status}",
        {
            "status": status,
            "company_name": company_name,
            "profile_link": f"{fe}/user/{artist.username}?tab=experience&workExpId={work_exp_id}",
            "home_link": fe,
        },
        "mail_work_exp_status.html",
    )


async def notify_company_suspension(
    db: AsyncSession,
    *,
    owner: UsersOrm,
    company_name: str,
    company_id: int,
    suspended: bool,
    reason: str | None = None,
) -> None:
    update_type = (
        UPDATE_TYPE_COMPANY_SUSPENDED if suspended else UPDATE_TYPE_COMPANY_UNSUSPENDED
    )
    label = "suspended" if suspended else "unsuspended"
    meta = {"company_id": company_id, "suspended": suspended}
    await create_in_app_update(
        db,
        to_user_id=owner.id,
        update_type=update_type,
        content=f"Company {label}: {company_name}"[:100],
        actor_user_id=None,
        metadata=meta,
    )
    fe = settings.FRONTEND_DOMAIN.rstrip("/")
    _safe_email(
        [str(owner.email)] if owner.email else [],
        f"Company {label} - {company_name}",
        {
            "company_name": company_name,
            "status": label,
            "reason": reason or "",
            "profile_link": f"{fe}/user/{owner.username}?tab=company",
            "home_link": fe,
        },
        "mail_company_suspension.html",
    )
