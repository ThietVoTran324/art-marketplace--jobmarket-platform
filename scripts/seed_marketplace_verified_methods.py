"""Seed a demo seller ready to list (Marketplace Sprint6+).

Idempotent for usernames in MP_SEED_VERIFY_USERNAMES (comma) or default demo_seller.

Does:
- ensure user exists (password TestPass123! if created)
- email verified
- enough pins + pin_stats views + followers for N/M/K
- verified active payment method (gate P)
- assign role seller

Does NOT list a pin (list from PinView).

Usage:
  docker exec fastapi-container python -m scripts.seed_marketplace_verified_methods
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update

from app.api.rest.roles import assign_role
from app.api.rest.utils import hash_password
from app.config import settings
from app.postgresql.database import async_session_maker
from app.postgresql.models import (
    PinStatsOrm,
    PinsOrm,
    SellerPaymentMethodsOrm,
    SubsrciptionsOrm,
    UsersOrm,
)

DEFAULT_USERNAMES = ("demo_seller",)
PASSWORD = "TestPass123!"


def usernames() -> list[str]:
    raw = (os.getenv("MP_SEED_VERIFY_USERNAMES") or "").strip()
    if raw:
        return [u.strip() for u in raw.split(",") if u.strip()]
    return list(DEFAULT_USERNAMES)

async def ensure_user(session, username: str) -> UsersOrm:
    user = await session.scalar(select(UsersOrm).where(UsersOrm.username == username))
    if user is None:
        user = UsersOrm(
            username=username,
            hashed_password=hash_password(PASSWORD),
            email=f"{username}@example.com",
            verified=True,
        )
        session.add(user)
        await session.flush()
        print(f"created user {username} / {PASSWORD}")
    else:
        await session.execute(
            update(UsersOrm)
            .where(UsersOrm.id == user.id)
            .values(
                verified=True,
                email=user.email or f"{username}@example.com",
            )
        )
        await session.refresh(user)
        print(f"verified email for existing user {username}")
    return user


async def ensure_nm_k(session, user: UsersOrm) -> None:
    min_n = settings.MP_ELIGIBILITY_MIN_PINS
    min_m = settings.MP_ELIGIBILITY_MIN_VIEWS
    min_k = settings.MP_ELIGIBILITY_MIN_FOLLOWERS

    pin_ids = list(
        (
            await session.scalars(select(PinsOrm.id).where(PinsOrm.user_id == user.id))
        ).all()
    )
    # Minimal pin rows without full media pipeline (eligibility counts pins only).
    while len(pin_ids) < min_n:
        pin = PinsOrm(
            user_id=user.id,
            title=f"seed pin {len(pin_ids)+1}",
            description="seed",
            image=None,
            original_image=None,
        )
        session.add(pin)
        await session.flush()
        pin_ids.append(pin.id)

    per_views = max(1, (min_m + len(pin_ids) - 1) // len(pin_ids))
    for pid in pin_ids:
        existing = await session.get(PinStatsOrm, pid)
        if existing is None:
            session.add(PinStatsOrm(pin_id=pid, view_count=per_views))
        elif int(existing.view_count or 0) < per_views:
            existing.view_count = per_views

    follower_count = int(
        await session.scalar(
            select(func.count())
            .select_from(SubsrciptionsOrm)
            .where(SubsrciptionsOrm.following_id == user.id)
        )
        or 0
    )
    for i in range(max(0, min_k - follower_count)):
        fname = f"seed_f_{user.id}_{i}_{uuid.uuid4().hex[:4]}"
        follower = UsersOrm(
            username=fname,
            hashed_password="x",
            verified=False,
        )
        session.add(follower)
        await session.flush()
        session.add(
            SubsrciptionsOrm(follower_id=follower.id, following_id=user.id)
        )


async def ensure_verified_method(session, user: UsersOrm) -> None:
    methods = list(
        (
            await session.scalars(
                select(SellerPaymentMethodsOrm).where(
                    SellerPaymentMethodsOrm.user_id == user.id
                )
            )
        ).all()
    )
    if not methods:
        session.add(
            SellerPaymentMethodsOrm(
                user_id=user.id,
                method_type="bank",
                display_name="Demo verified bank",
                account_identifier="0123456789",
                bank_code="970436",
                bank_name="Vietcombank",
                account_holder=user.username,
                is_active=True,
                is_primary=True,
                verification_status="verified",
                verified_at=datetime.now(timezone.utc),
                verified_by="seed",
            )
        )
        print(f"created verified payment method for {user.username}")
        return

    await session.execute(
        update(SellerPaymentMethodsOrm)
        .where(SellerPaymentMethodsOrm.user_id == user.id)
        .values(
            is_active=True,
            verification_status="verified",
            verified_at=datetime.now(timezone.utc),
            verified_by="seed",
        )
    )
    # Ensure at least one primary
    first = await session.scalar(
        select(SellerPaymentMethodsOrm)
        .where(SellerPaymentMethodsOrm.user_id == user.id)
        .order_by(SellerPaymentMethodsOrm.id.asc())
        .limit(1)
    )
    if first is not None:
        await session.execute(
            update(SellerPaymentMethodsOrm)
            .where(SellerPaymentMethodsOrm.user_id == user.id)
            .values(is_primary=False)
        )
        first.is_primary = True
    print(f"verified+activated methods for {user.username}")


async def seed_one(session, username: str) -> None:
    user = await ensure_user(session, username)
    await ensure_nm_k(session, user)
    await ensure_verified_method(session, user)
    await assign_role(session, user.id, "seller")
    print(f"seller role ensured for {username} (user_id={user.id})")


async def main() -> None:
    names = usernames()
    async with async_session_maker() as session:
        for name in names:
            await seed_one(session, name)
        await session.commit()
    print("SEED_OK")
    print(
        "Next: log in as seller → open a pin with original+preview → List for sale. "
        "Buyer needs another account with verified email."
    )


if __name__ == "__main__":
    asyncio.run(main())
