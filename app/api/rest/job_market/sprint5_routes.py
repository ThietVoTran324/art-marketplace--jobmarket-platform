"""JobMarket Sprint5 — work-exp approve, employees, suggest."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import aliased

from app.api.rest.audit import (
    ACTION_WORK_EXP_APPROVE,
    ACTION_WORK_EXP_REJECT,
    TARGET_WORK_EXP,
    write_audit,
)
from app.api.rest.dependencies import db, require_roles, user_id
from app.api.rest.ownership import assert_company_owner
from app.postgresql.models import (
    CompaniesOrm,
    CompanyEmployeeHeadsOrm,
    UsersOrm,
    WorkExperiencesOrm,
)

from .notify import notify_artist_work_exp_status
from .schemas import (
    CompanySuggestOut,
    EmployeeHeadCreate,
    EmployeeHeadOut,
    EmployeeHeadUpdate,
    EmployeeOut,
    EmployeesListOut,
    PendingWorkExperienceOut,
    WorkExperienceOut,
)
from .text_normalize import fold_search_text

router = APIRouter()
AdminUserId = Annotated[int, Depends(require_roles("admin"))]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return datetime.now(timezone.utc).date()


async def _get_owned_company_any_status(db, owner_id: int) -> CompaniesOrm | None:
    return await db.scalar(
        select(CompaniesOrm).where(CompaniesOrm.owner_user_id == owner_id)
    )


async def _get_owned_active_company(db, owner_id: int) -> CompaniesOrm | None:
    return await db.scalar(
        select(CompaniesOrm).where(
            CompaniesOrm.owner_user_id == owner_id,
            CompaniesOrm.status == "active",
        )
    )


async def _present_user_ids(db, company_id: int) -> set[int]:
    today = _today()
    rows = (
        await db.scalars(
            select(WorkExperiencesOrm).where(
                WorkExperiencesOrm.company_id == company_id,
                WorkExperiencesOrm.status == "approved",
                or_(
                    WorkExperiencesOrm.end_date.is_(None),
                    WorkExperiencesOrm.end_date >= today,
                ),
            )
        )
    ).all()
    return {r.user_id for r in rows}


async def _prune_stale_heads(db, company_id: int) -> None:
    present = await _present_user_ids(db, company_id)
    heads = (
        await db.scalars(
            select(CompanyEmployeeHeadsOrm).where(
                CompanyEmployeeHeadsOrm.company_id == company_id
            )
        )
    ).all()
    stale_ids = [h.id for h in heads if h.user_id not in present]
    if stale_ids:
        await db.execute(
            delete(CompanyEmployeeHeadsOrm).where(
                CompanyEmployeeHeadsOrm.id.in_(stale_ids)
            )
        )


async def _can_decide_work_exp(
    db, *, actor_id: int, work_exp: WorkExperiencesOrm, as_admin: bool
) -> CompaniesOrm:
    if work_exp.company_id is None:
        raise HTTPException(status_code=422, detail="work experience has no company_id")
    company = await db.scalar(
        select(CompaniesOrm).where(CompaniesOrm.id == work_exp.company_id)
    )
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    if company.status != "active":
        raise HTTPException(status_code=403, detail="company not active")
    if as_admin:
        return company
    if company.owner_user_id != actor_id:
        raise HTTPException(status_code=403, detail="not company owner")
    return company


async def _decide(
    db,
    *,
    actor_id: int,
    work_exp_id: int,
    new_status: str,
    as_admin: bool,
) -> WorkExperienceOut:
    row = await db.scalar(
        select(WorkExperiencesOrm).where(WorkExperiencesOrm.id == work_exp_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="work experience not found")

    company = await _can_decide_work_exp(
        db, actor_id=actor_id, work_exp=row, as_admin=as_admin
    )

    if new_status == "approved" and row.status == "approved":
        return row

    if row.status not in ("pending", "approved", "rejected"):
        raise HTTPException(status_code=422, detail="invalid status")

    if new_status == "rejected" and row.status == "rejected":
        return row

    row.status = new_status
    row.updated_at = _now()

    action = (
        ACTION_WORK_EXP_APPROVE if new_status == "approved" else ACTION_WORK_EXP_REJECT
    )
    await write_audit(
        db,
        actor_user_id=actor_id,
        action=action,
        target_type=TARGET_WORK_EXP,
        target_id=row.id,
        metadata={
            "company_id": company.id,
            "artist_user_id": row.user_id,
            "status": new_status,
            "as_admin": as_admin,
        },
    )

    artist = await db.scalar(select(UsersOrm).where(UsersOrm.id == row.user_id))
    if artist is not None:
        await notify_artist_work_exp_status(
            db,
            artist=artist,
            owner_id=actor_id,
            work_exp_id=row.id,
            status=new_status,
            company_name=row.company_name,
        )

    await _prune_stale_heads(db, company.id)
    await db.commit()
    await db.refresh(row)
    return row


# ---- Suggest ----


@router.get("/company-suggestions", response_model=list[CompanySuggestOut])
async def suggest_companies(
    db: db,
    user_id: user_id,
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
):
    """
    Suggest active companies by memorable fields: display_name + domain.
    Case- and Vietnamese-diacritic-insensitive (app-side fold; fine while N is small).
    Rank: exact name > exact domain > starts-with > contains (#15+#16 lite).
    """
    needle = fold_search_text(q)
    if not needle:
        return []

    # Cap scan; fold cannot use plain ILIKE. Revisit with unaccent+index if catalog grows large.
    candidates = (
        await db.scalars(
            select(CompaniesOrm)
            .where(CompaniesOrm.status == "active")
            .order_by(CompaniesOrm.display_name.asc())
            .limit(500)
        )
    ).all()

    scored: list[tuple[int, str, CompaniesOrm]] = []
    for row in candidates:
        name_fold = fold_search_text(row.display_name)
        domain_fold = fold_search_text(row.domain)
        score = 0
        if name_fold == needle:
            score = 100
        elif domain_fold and domain_fold == needle:
            score = 90
        elif name_fold.startswith(needle) or (
            domain_fold and domain_fold.startswith(needle)
        ):
            score = 50
        elif needle in name_fold or (domain_fold and needle in domain_fold):
            # Prefer word-start contains slightly over mid-token contains.
            word_hit = any(
                part.startswith(needle)
                for part in name_fold.replace(".", " ").split()
                if part
            ) or (
                domain_fold is not None
                and any(
                    part.startswith(needle)
                    for part in domain_fold.replace(".", " ").split()
                    if part
                )
            )
            score = 30 if word_hit else 10
        if score:
            scored.append((score, name_fold, row))

    scored.sort(key=lambda t: (-t[0], t[1]))
    return [row for _, _, row in scored[:limit]]


# ---- Pending / approve / reject (owner) ----


@router.get(
    "/me/company/work-experiences/pending",
    response_model=list[PendingWorkExperienceOut],
)
async def list_pending_work_experiences(db: db, user_id: user_id):
    company = await _get_owned_active_company(db, user_id)
    if company is None:
        # owner of non-active company may still read pending config? BR: owner reads employees
        # but approve needs active. Pending list for review only on active.
        company = await _get_owned_company_any_status(db, user_id)
        if company is None:
            raise HTTPException(status_code=403, detail="not company owner")

    artist = aliased(UsersOrm)
    rows = (
        await db.execute(
            select(WorkExperiencesOrm, artist.username, artist.id)
            .join(artist, artist.id == WorkExperiencesOrm.user_id)
            .where(
                WorkExperiencesOrm.company_id == company.id,
                WorkExperiencesOrm.status == "pending",
            )
            .order_by(WorkExperiencesOrm.created_at.asc(), WorkExperiencesOrm.id.asc())
        )
    ).all()
    out: list[PendingWorkExperienceOut] = []
    for we, username, artist_id in rows:
        item = PendingWorkExperienceOut.model_validate(we)
        item.artist_username = username
        item.artist_user_id = artist_id
        out.append(item)
    return out


@router.post(
    "/me/company/work-experiences/{work_exp_id}/approve",
    response_model=WorkExperienceOut,
)
async def owner_approve_work_experience(work_exp_id: int, db: db, user_id: user_id):
    return await _decide(
        db, actor_id=user_id, work_exp_id=work_exp_id, new_status="approved", as_admin=False
    )


@router.post(
    "/me/company/work-experiences/{work_exp_id}/reject",
    response_model=WorkExperienceOut,
)
async def owner_reject_work_experience(work_exp_id: int, db: db, user_id: user_id):
    return await _decide(
        db, actor_id=user_id, work_exp_id=work_exp_id, new_status="rejected", as_admin=False
    )


@router.get(
    "/admin/work-experiences",
    response_model=list[PendingWorkExperienceOut],
)
async def admin_list_work_experiences(
    db: db,
    admin_user_id: AdminUserId,
    status_filter: str | None = Query(default="pending", alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    _ = admin_user_id
    if status_filter is not None and status_filter not in (
        "pending",
        "approved",
        "rejected",
    ):
        raise HTTPException(status_code=422, detail="invalid status")

    artist = aliased(UsersOrm)
    stmt = (
        select(WorkExperiencesOrm, artist.username, artist.id)
        .join(artist, artist.id == WorkExperiencesOrm.user_id)
        .order_by(WorkExperiencesOrm.created_at.asc(), WorkExperiencesOrm.id.asc())
        .offset(offset)
        .limit(limit)
    )
    if status_filter is not None:
        stmt = stmt.where(WorkExperiencesOrm.status == status_filter)

    rows = (await db.execute(stmt)).all()
    out: list[PendingWorkExperienceOut] = []
    for we, username, artist_id in rows:
        item = PendingWorkExperienceOut.model_validate(we)
        item.artist_username = username
        item.artist_user_id = artist_id
        out.append(item)
    return out


@router.post(
    "/admin/work-experiences/{work_exp_id}/approve",
    response_model=WorkExperienceOut,
)
async def admin_approve_work_experience(
    work_exp_id: int, db: db, admin_user_id: AdminUserId
):
    return await _decide(
        db,
        actor_id=admin_user_id,
        work_exp_id=work_exp_id,
        new_status="approved",
        as_admin=True,
    )


@router.post(
    "/admin/work-experiences/{work_exp_id}/reject",
    response_model=WorkExperienceOut,
)
async def admin_reject_work_experience(
    work_exp_id: int, db: db, admin_user_id: AdminUserId
):
    return await _decide(
        db,
        actor_id=admin_user_id,
        work_exp_id=work_exp_id,
        new_status="rejected",
        as_admin=True,
    )


# ---- Employees ----


@router.get("/companies/{company_id}/employees", response_model=EmployeesListOut)
async def list_company_employees(company_id: int, db: db, user_id: user_id):
    company = await db.scalar(select(CompaniesOrm).where(CompaniesOrm.id == company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    is_owner = company.owner_user_id == user_id
    if company.status != "active" and not is_owner:
        raise HTTPException(status_code=404, detail="company not found")

    if not company.employees_public and not is_owner:
        raise HTTPException(status_code=403, detail="employees private")

    await _prune_stale_heads(db, company_id)
    await db.flush()

    today = _today()
    rows = (
        await db.scalars(
            select(WorkExperiencesOrm)
            .where(
                WorkExperiencesOrm.company_id == company_id,
                WorkExperiencesOrm.status == "approved",
                or_(
                    WorkExperiencesOrm.end_date.is_(None),
                    WorkExperiencesOrm.end_date >= today,
                ),
            )
            .order_by(WorkExperiencesOrm.start_date.asc(), WorkExperiencesOrm.id.asc())
        )
    ).all()

    # Dedupe by user: keep earliest start_date
    by_user: dict[int, WorkExperiencesOrm] = {}
    for r in rows:
        prev = by_user.get(r.user_id)
        if prev is None or r.start_date < prev.start_date or (
            r.start_date == prev.start_date and r.id < prev.id
        ):
            by_user[r.user_id] = r

    ordered = sorted(by_user.values(), key=lambda x: (x.start_date, x.id))
    user_ids = [r.user_id for r in ordered]
    usernames: dict[int, str | None] = {}
    if user_ids:
        for u in (
            await db.scalars(select(UsersOrm).where(UsersOrm.id.in_(user_ids)))
        ).all():
            usernames[u.id] = u.username

    employees = [
        EmployeeOut(
            user_id=r.user_id,
            username=usernames.get(r.user_id),
            title=r.title,
            start_date=r.start_date,
            work_experience_id=r.id,
        )
        for r in ordered
    ]

    heads_rows = (
        await db.scalars(
            select(CompanyEmployeeHeadsOrm)
            .where(CompanyEmployeeHeadsOrm.company_id == company_id)
            .order_by(
                CompanyEmployeeHeadsOrm.sort_order.asc(),
                CompanyEmployeeHeadsOrm.id.asc(),
            )
        )
    ).all()
    head_user_ids = [h.user_id for h in heads_rows]
    head_names: dict[int, str | None] = {}
    if head_user_ids:
        for u in (
            await db.scalars(select(UsersOrm).where(UsersOrm.id.in_(head_user_ids)))
        ).all():
            head_names[u.id] = u.username

    heads = [
        EmployeeHeadOut(
            id=h.id,
            company_id=h.company_id,
            user_id=h.user_id,
            username=head_names.get(h.user_id),
            title=h.title,
            note=h.note,
            sort_order=h.sort_order,
        )
        for h in heads_rows
    ]

    if not company.employees_public and not is_owner:
        raise HTTPException(status_code=403, detail="employees private")

    return EmployeesListOut(
        employees_public=company.employees_public,
        employees=employees,
        heads=heads,
    )


@router.post(
    "/me/company/employee-heads",
    response_model=EmployeeHeadOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_employee_head(body: EmployeeHeadCreate, db: db, user_id: user_id):
    company = await _get_owned_active_company(db, user_id)
    if company is None:
        raise HTTPException(status_code=403, detail="not company owner")
    await assert_company_owner(db, company.id, user_id)

    present = await _present_user_ids(db, company.id)
    if body.user_id not in present:
        raise HTTPException(status_code=422, detail="user not present employee")

    existing = await db.scalar(
        select(CompanyEmployeeHeadsOrm).where(
            CompanyEmployeeHeadsOrm.company_id == company.id,
            CompanyEmployeeHeadsOrm.user_id == body.user_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="head already exists")

    row = CompanyEmployeeHeadsOrm(
        company_id=company.id,
        user_id=body.user_id,
        title=body.title,
        note=body.note,
        sort_order=body.sort_order,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == row.user_id))
    return EmployeeHeadOut(
        id=row.id,
        company_id=row.company_id,
        user_id=row.user_id,
        username=user.username if user else None,
        title=row.title,
        note=row.note,
        sort_order=row.sort_order,
    )


@router.patch(
    "/me/company/employee-heads/{head_id}",
    response_model=EmployeeHeadOut,
)
async def update_employee_head(
    head_id: int, body: EmployeeHeadUpdate, db: db, user_id: user_id
):
    company = await _get_owned_active_company(db, user_id)
    if company is None:
        raise HTTPException(status_code=403, detail="not company owner")
    row = await db.scalar(
        select(CompanyEmployeeHeadsOrm).where(
            CompanyEmployeeHeadsOrm.id == head_id,
            CompanyEmployeeHeadsOrm.company_id == company.id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="head not found")

    for key, value in body.model_dump(exclude_none=True).items():
        setattr(row, key, value)
    row.updated_at = _now()
    await db.commit()
    await db.refresh(row)
    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == row.user_id))
    return EmployeeHeadOut(
        id=row.id,
        company_id=row.company_id,
        user_id=row.user_id,
        username=user.username if user else None,
        title=row.title,
        note=row.note,
        sort_order=row.sort_order,
    )


@router.delete(
    "/me/company/employee-heads/{head_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_employee_head(head_id: int, db: db, user_id: user_id):
    company = await _get_owned_active_company(db, user_id)
    if company is None:
        raise HTTPException(status_code=403, detail="not company owner")
    row = await db.scalar(
        select(CompanyEmployeeHeadsOrm).where(
            CompanyEmployeeHeadsOrm.id == head_id,
            CompanyEmployeeHeadsOrm.company_id == company.id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="head not found")
    await db.execute(
        delete(CompanyEmployeeHeadsOrm).where(CompanyEmployeeHeadsOrm.id == head_id)
    )
    await db.commit()
