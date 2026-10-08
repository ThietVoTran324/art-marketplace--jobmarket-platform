"""Company career-path follows (separate from user pin follows)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError

from app.api.rest.dependencies import db, optional_user_id, user_id
from app.postgresql.models import CompaniesOrm, company_follows

router = APIRouter()


async def _active_company(db, company_id: int) -> CompaniesOrm:
    company = await db.scalar(select(CompaniesOrm).where(CompaniesOrm.id == company_id))
    if company is None or company.status != "active":
        raise HTTPException(status_code=404, detail="company not found")
    return company


@router.post(
    "/companies/{company_id}/follow",
    status_code=status.HTTP_201_CREATED,
)
async def follow_company(company_id: int, db: db, user_id: user_id):
    company = await _active_company(db, company_id)
    if company.owner_user_id == user_id:
        raise HTTPException(status_code=409, detail="cannot_follow_own_company")
    try:
        await db.execute(
            insert(company_follows).values(user_id=user_id, company_id=company_id)
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="already_following")
    return {"status": "ok"}


@router.delete(
    "/companies/{company_id}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unfollow_company(company_id: int, db: db, user_id: user_id):
    await _active_company(db, company_id)
    await db.execute(
        delete(company_follows).where(
            company_follows.c.user_id == user_id,
            company_follows.c.company_id == company_id,
        )
    )
    await db.commit()
    return None


@router.get("/companies/{company_id}/follow/status")
async def company_follow_status(
    company_id: int, db: db, user_id: optional_user_id
):
    await _active_company(db, company_id)
    if user_id is None:
        return {"following": False}
    row = (
        await db.execute(
            select(company_follows.c.company_id).where(
                company_follows.c.user_id == user_id,
                company_follows.c.company_id == company_id,
            )
        )
    ).first()
    return {"following": row is not None}
