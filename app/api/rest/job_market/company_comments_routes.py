"""Company page comments — same shape as pin comments + employment badge."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, insert, select

from app.api.rest.comments.schemas import CommentIn
from app.api.rest.dependencies import db, filter, optional_user_id, user_id
from app.postgresql.models import CommentsOrm, CompaniesOrm, WorkExperiencesOrm

from .schemas import CompanyCommentOut

router = APIRouter()


def _today() -> date:
    return datetime.now(timezone.utc).date()


async def _assert_active_company(db, company_id: int) -> CompaniesOrm:
    company = await db.scalar(select(CompaniesOrm).where(CompaniesOrm.id == company_id))
    if company is None or company.status != "active":
        raise HTTPException(status_code=404, detail="company not found")
    return company


async def _employment_map(
    db, company_id: int, user_ids: list[int]
) -> dict[int, str]:
    """user_id -> current | former (current wins if both)."""
    if not user_ids:
        return {}
    today = _today()
    rows = (
        await db.scalars(
            select(WorkExperiencesOrm).where(
                WorkExperiencesOrm.company_id == company_id,
                WorkExperiencesOrm.status == "approved",
                WorkExperiencesOrm.user_id.in_(user_ids),
            )
        )
    ).all()
    out: dict[int, str] = {}
    for r in rows:
        is_current = r.end_date is None or r.end_date >= today
        if is_current:
            out[r.user_id] = "current"
        elif out.get(r.user_id) != "current":
            out[r.user_id] = "former"
    return out


def _to_out(row: CommentsOrm, status_map: dict[int, str]) -> CompanyCommentOut:
    return CompanyCommentOut(
        id=row.id,
        company_id=row.company_id,
        user_id=row.user_id,
        comment_id=row.comment_id,
        content=row.content,
        created_at=row.created_at,
        image=row.image,
        employment_status=status_map.get(row.user_id),
    )


@router.get(
    "/companies/{company_id}/comments",
    response_model=list[CompanyCommentOut],
)
async def list_company_comments(
    company_id: int,
    db: db,
    user_id: optional_user_id,
    filter: filter,
):
    _ = user_id
    await _assert_active_company(db, company_id)
    rows = list(
        (
            await db.scalars(
                select(CommentsOrm)
                .where(
                    CommentsOrm.company_id == company_id,
                    CommentsOrm.comment_id.is_(None),
                )
                .order_by(CommentsOrm.id.desc())
                .offset(filter.offset)
                .limit(filter.limit)
            )
        ).all()
    )
    status_map = await _employment_map(db, company_id, [r.user_id for r in rows])
    return [_to_out(r, status_map) for r in rows]


@router.get("/companies/{company_id}/comments/count")
async def count_company_comments(
    company_id: int, db: db, user_id: optional_user_id
):
    _ = user_id
    await _assert_active_company(db, company_id)
    return int(
        await db.scalar(
            select(func.count())
            .select_from(CommentsOrm)
            .where(
                CommentsOrm.company_id == company_id,
                CommentsOrm.comment_id.is_(None),
            )
        )
        or 0
    )


@router.post(
    "/companies/{company_id}/comments",
    response_model=CompanyCommentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_company_comment(
    company_id: int, body: CommentIn, db: db, user_id: user_id
):
    await _assert_active_company(db, company_id)
    if not (body.content or "").strip():
        raise HTTPException(status_code=422, detail="content required")
    row = await db.scalar(
        insert(CommentsOrm)
        .values(
            content=body.content.strip(),
            company_id=company_id,
            user_id=user_id,
            pin_id=None,
        )
        .returning(CommentsOrm)
    )
    await db.commit()
    status_map = await _employment_map(db, company_id, [user_id])
    return _to_out(row, status_map)
