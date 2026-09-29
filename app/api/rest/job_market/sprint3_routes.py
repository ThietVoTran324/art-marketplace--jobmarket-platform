"""JobMarket Sprint3 — job posts, explore, company hiring list."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import case, delete, func, or_, select

from app.api.rest.dependencies import db, user_id
from app.api.rest.ownership import assert_job_post_company_owner
from app.api.rest.roles import get_user_roles
from app.postgresql.models import (
    CompaniesOrm,
    CompanyBranchesOrm,
    JobApplicationsOrm,
    JobPostLocationsOrm,
    JobPostsOrm,
)

from .constants import (
    DEFAULT_CURRENCY,
    JOB_STATUS_ACTIVE,
    JOB_STATUS_CLOSED,
    SALARY_MODE_LOVE_IT,
    SALARY_MODE_RANGE,
)
from .schemas import JobPostCreate, JobPostOut, JobPostUpdate, MyApplicationBrief

router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _require_owned_active_company(db, user_id: int) -> CompaniesOrm:
    roles = await get_user_roles(db, user_id)
    if "employer" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="hiring_rights_required",
        )
    company = await db.scalar(
        select(CompaniesOrm).where(
            CompaniesOrm.owner_user_id == user_id,
            CompaniesOrm.status == "active",
        )
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not company owner",
        )
    return company


async def _require_owned_company(db, user_id: int) -> CompaniesOrm:
    roles = await get_user_roles(db, user_id)
    if "employer" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="hiring_rights_required",
        )
    company = await db.scalar(
        select(CompaniesOrm).where(
            CompaniesOrm.owner_user_id == user_id,
            CompaniesOrm.status.in_(("active", "suspended")),
        )
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not company owner",
        )
    return company


async def _ensure_company_active_for_jd_mutate(db, company_id: int) -> CompaniesOrm:
    company = await db.scalar(select(CompaniesOrm).where(CompaniesOrm.id == company_id))
    if company is None or company.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="company_not_active",
        )
    return company


async def _load_locations(db, job_post_id: int) -> list[JobPostLocationsOrm]:
    return list(
        (
            await db.scalars(
                select(JobPostLocationsOrm)
                .where(JobPostLocationsOrm.job_post_id == job_post_id)
                .order_by(JobPostLocationsOrm.id.asc())
            )
        ).all()
    )


async def _job_out(
    db,
    row: JobPostsOrm,
    *,
    company_display_name: str | None = None,
    application_count: int | None = None,
) -> JobPostOut:
    locs = await _load_locations(db, row.id)
    out = JobPostOut.model_validate(row)
    out.locations = [loc for loc in locs]
    if company_display_name is not None:
        out.company_display_name = company_display_name
    elif out.company_display_name is None:
        company = await db.scalar(
            select(CompaniesOrm).where(CompaniesOrm.id == row.company_id)
        )
        if company is not None:
            out.company_display_name = company.display_name
    if application_count is not None:
        out.application_count = application_count
    else:
        out.application_count = int(
            await db.scalar(
                select(func.count())
                .select_from(JobApplicationsOrm)
                .where(JobApplicationsOrm.job_post_id == row.id)
            )
            or 0
        )
    return out


async def _replace_locations_from_branches(
    db, *, job_post_id: int, company_id: int, branch_ids: list[int]
) -> None:
    unique_ids = list(dict.fromkeys(branch_ids))
    if not unique_ids:
        raise HTTPException(status_code=400, detail="branch_ids required")

    branches = list(
        (
            await db.scalars(
                select(CompanyBranchesOrm).where(
                    CompanyBranchesOrm.company_id == company_id,
                    CompanyBranchesOrm.id.in_(unique_ids),
                )
            )
        ).all()
    )
    if len(branches) != len(unique_ids):
        raise HTTPException(
            status_code=400,
            detail="one or more branch_ids invalid for this company",
        )

    await db.execute(
        delete(JobPostLocationsOrm).where(JobPostLocationsOrm.job_post_id == job_post_id)
    )
    for branch in branches:
        db.add(
            JobPostLocationsOrm(
                job_post_id=job_post_id,
                source_branch_id=branch.id,
                label=branch.label,
                address_line=branch.address_line,
                city=branch.city,
                country=branch.country,
            )
        )


def _apply_salary_fields(
    row: JobPostsOrm,
    *,
    salary_mode: str | None,
    salary_min: int | None,
    salary_max: int | None,
    currency: str | None,
    mode_provided: bool,
    min_provided: bool,
    max_provided: bool,
) -> None:
    mode = salary_mode if mode_provided else row.salary_mode
    if mode == SALARY_MODE_LOVE_IT:
        row.salary_mode = SALARY_MODE_LOVE_IT
        row.salary_min = None
        row.salary_max = None
    else:
        new_min = salary_min if min_provided else row.salary_min
        new_max = salary_max if max_provided else row.salary_max
        if mode_provided:
            row.salary_mode = SALARY_MODE_RANGE
        if min_provided:
            row.salary_min = salary_min
        if max_provided:
            row.salary_max = salary_max
        if row.salary_min is None and row.salary_max is None:
            raise HTTPException(
                status_code=422,
                detail="range requires at least one of salary_min or salary_max",
            )
        if (
            row.salary_min is not None
            and row.salary_max is not None
            and row.salary_max < row.salary_min
        ):
            raise HTTPException(
                status_code=422, detail="salary_max must be >= salary_min"
            )
        _ = new_min, new_max
    if currency is not None:
        row.currency = currency


# ---- Owner CRUD ----


@router.get("/me/job-posts", response_model=list[JobPostOut])
async def list_my_job_posts(
    db: db,
    user_id: user_id,
    status_filter: str | None = Query(default=None, alias="status"),
):
    company = await _require_owned_company(db, user_id)
    stmt = select(JobPostsOrm).where(JobPostsOrm.company_id == company.id)
    if status_filter is not None:
        if status_filter not in (JOB_STATUS_ACTIVE, JOB_STATUS_CLOSED):
            raise HTTPException(status_code=422, detail="invalid status")
        stmt = stmt.where(JobPostsOrm.status == status_filter)
    stmt = stmt.order_by(JobPostsOrm.created_at.desc(), JobPostsOrm.id.desc())
    rows = (await db.scalars(stmt)).all()
    return [await _job_out(db, row, company_display_name=company.display_name) for row in rows]


@router.post(
    "/me/job-posts",
    response_model=JobPostOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_my_job_post(body: JobPostCreate, db: db, user_id: user_id):
    company = await _require_owned_active_company(db, user_id)
    expires_at = body.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= _now():
        raise HTTPException(status_code=422, detail="expires_at must be in the future")
    row = JobPostsOrm(
        company_id=company.id,
        title=body.title.strip(),
        years_experience=body.years_experience,
        description=body.description,
        requirements=body.requirements,
        benefits=body.benefits,
        salary_mode=body.salary_mode,
        salary_min=body.salary_min if body.salary_mode == SALARY_MODE_RANGE else None,
        salary_max=body.salary_max if body.salary_mode == SALARY_MODE_RANGE else None,
        currency=body.currency or DEFAULT_CURRENCY,
        status=JOB_STATUS_ACTIVE,
        expires_at=expires_at,
    )
    db.add(row)
    await db.flush()
    await _replace_locations_from_branches(
        db, job_post_id=row.id, company_id=company.id, branch_ids=body.branch_ids
    )
    await db.commit()
    await db.refresh(row)
    return await _job_out(db, row, company_display_name=company.display_name)


@router.get("/me/job-posts/{job_post_id}", response_model=JobPostOut)
async def get_my_job_post(job_post_id: int, db: db, user_id: user_id):
    row = await assert_job_post_company_owner(db, job_post_id, user_id)
    return await _job_out(db, row)


@router.patch("/me/job-posts/{job_post_id}", response_model=JobPostOut)
async def update_my_job_post(
    job_post_id: int, body: JobPostUpdate, db: db, user_id: user_id
):
    row = await assert_job_post_company_owner(db, job_post_id, user_id)
    await _ensure_company_active_for_jd_mutate(db, row.company_id)
    data = body.model_dump(exclude_unset=True)
    branch_ids = data.pop("branch_ids", None)

    for key in ("title", "years_experience", "description", "requirements", "benefits"):
        if key in data:
            value = data[key]
            if key == "title" and isinstance(value, str):
                value = value.strip()
            setattr(row, key, value)

    if "expires_at" in data and data["expires_at"] is not None:
        expires_at = data["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= _now():
            raise HTTPException(status_code=422, detail="expires_at must be in the future")
        row.expires_at = expires_at

    salary_keys = {"salary_mode", "salary_min", "salary_max", "currency"}
    if salary_keys & data.keys():
        _apply_salary_fields(
            row,
            salary_mode=data.get("salary_mode"),
            salary_min=data.get("salary_min"),
            salary_max=data.get("salary_max"),
            currency=data.get("currency"),
            mode_provided="salary_mode" in data,
            min_provided="salary_min" in data,
            max_provided="salary_max" in data,
        )
        if row.salary_mode == SALARY_MODE_LOVE_IT:
            row.salary_min = None
            row.salary_max = None

    if branch_ids is not None:
        await _replace_locations_from_branches(
            db,
            job_post_id=row.id,
            company_id=row.company_id,
            branch_ids=branch_ids,
        )

    row.updated_at = _now()
    await db.commit()
    await db.refresh(row)
    return await _job_out(db, row)


@router.post("/me/job-posts/{job_post_id}/close", response_model=JobPostOut)
async def close_my_job_post(job_post_id: int, db: db, user_id: user_id):
    row = await assert_job_post_company_owner(db, job_post_id, user_id)
    await _ensure_company_active_for_jd_mutate(db, row.company_id)
    row.status = JOB_STATUS_CLOSED
    row.updated_at = _now()
    await db.commit()
    await db.refresh(row)
    return await _job_out(db, row)


@router.post("/me/job-posts/{job_post_id}/reopen", response_model=JobPostOut)
async def reopen_my_job_post(job_post_id: int, db: db, user_id: user_id):
    row = await assert_job_post_company_owner(db, job_post_id, user_id)
    await _ensure_company_active_for_jd_mutate(db, row.company_id)
    if row.expires_at <= _now():
        raise HTTPException(
            status_code=422,
            detail="expires_at_must_be_extended",
        )
    row.status = JOB_STATUS_ACTIVE
    row.hiring_cycle = int(row.hiring_cycle or 0) + 1
    row.updated_at = _now()
    await db.commit()
    await db.refresh(row)
    return await _job_out(db, row)


# ---- Public-to-login: company hiring + explore + detail ----


@router.get("/companies/{company_id}/job-posts", response_model=list[JobPostOut])
async def list_company_job_posts(
    company_id: int,
    db: db,
    user_id: user_id,
    status_filter: str = Query(default=JOB_STATUS_ACTIVE, alias="status"),
):
    company = await db.scalar(select(CompaniesOrm).where(CompaniesOrm.id == company_id))
    if company is None or company.status != "active":
        raise HTTPException(status_code=404, detail="company not found")
    if status_filter not in (JOB_STATUS_ACTIVE, JOB_STATUS_CLOSED):
        raise HTTPException(status_code=422, detail="invalid status")
    # Visitors only see active; owner may request closed via status query if needed —
    # BR: Đang tuyển = active for visitor+owner. Keep default active; allow closed only for owner.
    if status_filter == JOB_STATUS_CLOSED and company.owner_user_id != user_id:
        raise HTTPException(status_code=403, detail="not company owner")
    now = _now()
    stmt = select(JobPostsOrm).where(
        JobPostsOrm.company_id == company_id,
        JobPostsOrm.status == status_filter,
    )
    # Public "Đang tuyển" hides expired active posts
    if status_filter == JOB_STATUS_ACTIVE:
        stmt = stmt.where(JobPostsOrm.expires_at > now)
    rows = (
        await db.scalars(stmt.order_by(JobPostsOrm.created_at.desc(), JobPostsOrm.id.desc()))
    ).all()
    return [
        await _job_out(db, row, company_display_name=company.display_name) for row in rows
    ]


@router.get("/explore/jobs", response_model=list[JobPostOut])
async def explore_jobs(
    db: db,
    user_id: user_id,
    q: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
):
    """Suggest / search list for explore. Filters (years/salary/…) are applied client-side.

    Suggest (empty q): highest salary first, then newest.
    Search (q set): title/company match, same salary→newest ranking.
    Only active + not-expired jobs from active companies.
    """
    _ = user_id
    now = _now()
    stmt = (
        select(JobPostsOrm, CompaniesOrm.display_name)
        .join(CompaniesOrm, CompaniesOrm.id == JobPostsOrm.company_id)
        .where(
            JobPostsOrm.status == JOB_STATUS_ACTIVE,
            CompaniesOrm.status == "active",
            JobPostsOrm.expires_at > now,
        )
    )

    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                JobPostsOrm.title.ilike(pattern),
                CompaniesOrm.display_name.ilike(pattern),
            )
        )

    # Suggest ranking: highest salary → newest (love_it ranks as 0)
    salary_rank = case(
        (JobPostsOrm.salary_mode == SALARY_MODE_LOVE_IT, 0),
        else_=func.coalesce(JobPostsOrm.salary_max, JobPostsOrm.salary_min, 0),
    )
    stmt = (
        stmt.order_by(salary_rank.desc(), JobPostsOrm.created_at.desc(), JobPostsOrm.id.desc())
        .offset(offset)
        .limit(limit)
    )
    pairs = (await db.execute(stmt)).all()
    if not pairs:
        return []

    job_ids = [row.id for row, _ in pairs]
    count_rows = (
        await db.execute(
            select(JobApplicationsOrm.job_post_id, func.count())
            .where(JobApplicationsOrm.job_post_id.in_(job_ids))
            .group_by(JobApplicationsOrm.job_post_id)
        )
    ).all()
    counts = {jid: int(cnt) for jid, cnt in count_rows}

    return [
        await _job_out(
            db,
            row,
            company_display_name=display_name,
            application_count=counts.get(row.id, 0),
        )
        for row, display_name in pairs
    ]


@router.get("/jobs/{job_post_id}", response_model=JobPostOut)
async def get_job_post(job_post_id: int, db: db, user_id: user_id):
    row = await db.scalar(select(JobPostsOrm).where(JobPostsOrm.id == job_post_id))
    if row is None:
        raise HTTPException(status_code=404, detail="job post not found")

    company = await db.scalar(
        select(CompaniesOrm).where(CompaniesOrm.id == row.company_id)
    )
    is_owner = (
        company is not None
        and company.owner_user_id == user_id
        and company.status in ("active", "suspended")
    )

    if row.status == JOB_STATUS_CLOSED and not is_owner:
        raise HTTPException(status_code=404, detail="job post not found")
    if not is_owner and (company is None or company.status != "active"):
        raise HTTPException(status_code=404, detail="job post not found")
    if not is_owner and row.expires_at <= _now():
        raise HTTPException(status_code=404, detail="job post not found")

    out = await _job_out(
        db,
        row,
        company_display_name=company.display_name if company else None,
    )
    mine = await db.scalar(
        select(JobApplicationsOrm)
        .where(
            JobApplicationsOrm.job_post_id == job_post_id,
            JobApplicationsOrm.applicant_user_id == user_id,
            JobApplicationsOrm.hiring_cycle == row.hiring_cycle,
        )
        .order_by(JobApplicationsOrm.created_at.desc(), JobApplicationsOrm.id.desc())
        .limit(1)
    )
    if mine is not None:
        out.my_application = MyApplicationBrief.model_validate(mine)
    return out
