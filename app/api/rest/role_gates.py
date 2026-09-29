"""Cross-domain role / account-kind gates for soft-live product rules.

Roles: admin, artist, employer, seller (multi).
account_kind organization = employer + owned company (active|suspended).
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rest.job_market.helpers import is_organization_user
from app.api.rest.roles import get_user_roles


async def is_admin_user(db: AsyncSession, user_id: int) -> bool:
    roles = await get_user_roles(db, user_id)
    return "admin" in roles


async def assert_not_admin(
    db: AsyncSession, user_id: int, *, detail: str = "admin_ops_only"
) -> None:
    if await is_admin_user(db, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def assert_not_organization(
    db: AsyncSession, user_id: int, *, detail: str = "org_not_allowed"
) -> None:
    if await is_organization_user(db, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def assert_can_apply_to_job(db: AsyncSession, user_id: int) -> None:
    """Personal applicants only — org and admin cannot apply."""
    if await is_organization_user(db, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="org_cannot_apply")
    await assert_not_admin(db, user_id, detail="admin_cannot_apply")


async def assert_can_manage_cv(db: AsyncSession, user_id: int) -> None:
    """CV is an applicant surface — organization accounts cannot mutate."""
    await assert_not_organization(db, user_id, detail="org_cannot_manage_cv")


async def assert_can_submit_hiring_kyc(db: AsyncSession, user_id: int) -> None:
    """Admin is ops-only; org already has hiring rights."""
    await assert_not_admin(db, user_id, detail="admin_cannot_submit_hiring_kyc")
    if await is_organization_user(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="already_has_hiring_rights"
        )


async def assert_can_sell_on_marketplace(db: AsyncSession, user_id: int) -> None:
    """Enable-selling / list — not admin, not organization (dual seller+org denied)."""
    await assert_not_admin(db, user_id, detail="admin_cannot_sell")
    await assert_not_organization(db, user_id, detail="org_cannot_sell")


async def assert_can_buy_license(db: AsyncSession, user_id: int) -> None:
    """Checkout buyer — not admin, not organization."""
    await assert_not_admin(db, user_id, detail="admin_cannot_buy")
    await assert_not_organization(db, user_id, detail="org_cannot_buy")


async def assert_can_create_pin(db: AsyncSession, user_id: int) -> None:
    """Pins are personal/brand-artist content — organization accounts cannot create."""
    await assert_not_organization(db, user_id, detail="org_cannot_create_pin")
