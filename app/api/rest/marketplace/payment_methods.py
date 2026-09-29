"""Helpers for seller payment methods (Sprint3 + Sprint6 verify)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.postgresql.models import PinListingsOrm, SellerPaymentMethodsOrm


async def count_active_methods(db: AsyncSession, user_id: int) -> int:
    return int(
        await db.scalar(
            select(func.count())
            .select_from(SellerPaymentMethodsOrm)
            .where(
                SellerPaymentMethodsOrm.user_id == user_id,
                SellerPaymentMethodsOrm.is_active.is_(True),
            )
        )
        or 0
    )


async def count_verified_active_methods(db: AsyncSession, user_id: int) -> int:
    return int(
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


def method_counts_toward_p(row: SellerPaymentMethodsOrm) -> bool:
    return bool(row.is_active and row.verification_status == "verified")


async def count_listed_pins(db: AsyncSession, user_id: int) -> int:
    return int(
        await db.scalar(
            select(func.count())
            .select_from(PinListingsOrm)
            .where(
                PinListingsOrm.seller_user_id == user_id,
                PinListingsOrm.status == "listed",
            )
        )
        or 0
    )


async def assert_can_drop_active_method(
    db: AsyncSession,
    user_id: int,
    *,
    remaining_active_after: int | None = None,
    remaining_verified_after: int | None = None,
    dropping_counts_toward_p: bool = False,
) -> None:
    """Block removing last P-qualifying method while listed.

    Sprint6: P = active+verified. Dropping an unverified method never blocks.
    """
    if not dropping_counts_toward_p:
        return
    remaining = (
        remaining_verified_after
        if remaining_verified_after is not None
        else (remaining_active_after if remaining_active_after is not None else 0)
    )
    if remaining > 0:
        return
    listed = await count_listed_pins(db, user_id)
    if listed > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cannot_remove_last_payout_while_listed",
        )


async def clear_other_primaries(
    db: AsyncSession, user_id: int, keep_method_id: int | None = None
) -> None:
    stmt = (
        update(SellerPaymentMethodsOrm)
        .where(
            SellerPaymentMethodsOrm.user_id == user_id,
            SellerPaymentMethodsOrm.is_primary.is_(True),
        )
        .values(is_primary=False)
    )
    if keep_method_id is not None:
        stmt = stmt.where(SellerPaymentMethodsOrm.id != keep_method_id)
    await db.execute(stmt)


async def get_owned_method(
    db: AsyncSession, user_id: int, method_id: int
) -> SellerPaymentMethodsOrm:
    row = await db.scalar(
        select(SellerPaymentMethodsOrm).where(SellerPaymentMethodsOrm.id == method_id)
    )
    if row is None or row.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="payment_method_not_found"
        )
    return row


async def set_method_verification(
    db: AsyncSession,
    method_id: int,
    *,
    verification_status: str,
    verified_by: str,
) -> SellerPaymentMethodsOrm:
    if verification_status not in ("unverified", "verified"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_verification_status"
        )
    row = await db.scalar(
        select(SellerPaymentMethodsOrm).where(SellerPaymentMethodsOrm.id == method_id)
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="payment_method_not_found"
        )

    if verification_status == "verified":
        values = {
            "verification_status": "verified",
            "verified_at": datetime.now(timezone.utc),
            "verified_by": verified_by,
        }
    else:
        if method_counts_toward_p(row):
            remaining = await count_verified_active_methods(db, row.user_id) - 1
            await assert_can_drop_active_method(
                db,
                row.user_id,
                remaining_verified_after=remaining,
                dropping_counts_toward_p=True,
            )
        values = {
            "verification_status": "unverified",
            "verified_at": None,
            "verified_by": None,
        }

    row = await db.scalar(
        update(SellerPaymentMethodsOrm)
        .where(SellerPaymentMethodsOrm.id == method_id)
        .values(**values)
        .returning(SellerPaymentMethodsOrm)
    )
    return row
