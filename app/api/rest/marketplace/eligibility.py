"""Marketplace Sprint2 — eligibility helpers."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rest.roles import get_user_roles
from app.api.rest.role_gates import assert_can_sell_on_marketplace
from app.config import settings
from app.postgresql.models import (
    PinStatsOrm,
    PinsOrm,
    SellerPaymentMethodsOrm,
    SubsrciptionsOrm,
)


@dataclass
class Criterion:
    code: str
    current: int
    threshold: int
    passed: bool


@dataclass
class EligibilityResult:
    criteria: list[Criterion]
    eligible: bool
    has_seller_role: bool

    def as_dict(self) -> dict:
        return {
            "eligible": self.eligible,
            "has_seller_role": self.has_seller_role,
            "criteria": [
                {
                    "code": c.code,
                    "current": c.current,
                    "threshold": c.threshold,
                    "passed": c.passed,
                }
                for c in self.criteria
            ],
        }


async def compute_eligibility(db: AsyncSession, user_id: int) -> EligibilityResult:
    n = int(
        await db.scalar(
            select(func.count()).select_from(PinsOrm).where(PinsOrm.user_id == user_id)
        )
        or 0
    )
    m = int(
        await db.scalar(
            select(func.coalesce(func.sum(PinStatsOrm.view_count), 0))
            .select_from(PinStatsOrm)
            .join(PinsOrm, PinsOrm.id == PinStatsOrm.pin_id)
            .where(PinsOrm.user_id == user_id)
        )
        or 0
    )
    k = int(
        await db.scalar(
            select(func.count())
            .select_from(SubsrciptionsOrm)
            .where(SubsrciptionsOrm.following_id == user_id)
        )
        or 0
    )
    p = int(
        await db.scalar(
            select(func.count())
            .select_from(SellerPaymentMethodsOrm)
            .where(
                SellerPaymentMethodsOrm.user_id == user_id,
                SellerPaymentMethodsOrm.is_active.is_(True),
                SellerPaymentMethodsOrm.verification_status == "verified",
            )
        )
        or 0
    )

    min_n = settings.MP_ELIGIBILITY_MIN_PINS
    min_m = settings.MP_ELIGIBILITY_MIN_VIEWS
    min_k = settings.MP_ELIGIBILITY_MIN_FOLLOWERS
    min_p = 1

    criteria = [
        Criterion("N", n, min_n, n >= min_n),
        Criterion("M", m, min_m, m >= min_m),
        Criterion("K", k, min_k, k >= min_k),
        Criterion("P", p, min_p, p >= min_p),
    ]
    roles = await get_user_roles(db, user_id)
    return EligibilityResult(
        criteria=criteria,
        eligible=all(c.passed for c in criteria),
        has_seller_role="seller" in roles,
    )


async def assert_can_create_listing(db: AsyncSession, user_id: int) -> EligibilityResult:
    await assert_can_sell_on_marketplace(db, user_id)
    roles = await get_user_roles(db, user_id)
    if "seller" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="seller_required")
    result = await compute_eligibility(db, user_id)
    if not result.eligible:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="listing_blocked_below_threshold",
        )
    return result
