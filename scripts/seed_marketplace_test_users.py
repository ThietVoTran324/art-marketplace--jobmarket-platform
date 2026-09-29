"""Seed Marketplace manual-test accounts via API + DB eligibility bumps.

Usage (inside fastapi container):
  PYTHONPATH=/fastapi python scripts/seed_marketplace_test_users.py
"""
from __future__ import annotations

import asyncio
import io
import uuid

import httpx
from PIL import Image
from sqlalchemy import text

from app.config import settings
from app.postgresql.database import async_session_maker

BASE = "http://127.0.0.1:8000"
PASSWORD = "MarketTest123!"
SUFFIX = "manual"


def csrf_headers(cookies: httpx.Cookies) -> dict[str, str]:
    token = cookies.get("csrf_token")
    assert token, "missing csrf_token"
    return {"X-CSRF-Token": token}


def png_bytes(color=(30, 100, 180)) -> bytes:
    img = Image.new("RGB", (220, 180), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def register_or_login(client: httpx.AsyncClient, username: str) -> tuple[int, httpx.Cookies]:
    r = await client.post(
        "/users/register", json={"username": username, "password": PASSWORD}
    )
    if r.status_code == 201:
        uid = r.json()["id"]
    else:
        # already exists — login
        async with async_session_maker() as session:
            uid = await session.scalar(
                text("SELECT id FROM users WHERE username = :u"), {"u": username}
            )
        assert uid, f"user missing and register failed: {r.text}"
    r = await client.post(
        "/users/login", json={"username": username, "password": PASSWORD}
    )
    assert r.status_code == 200, r.text
    return int(uid), r.cookies


async def create_pin(client, cookies, headers, title: str) -> int:
    files = {"file": ("t.png", png_bytes(), "image/png")}
    data = {"pin_model": f'{{"title":"{title}","description":"mp test"}}'}
    r = await client.post(
        "/pins/create-pin-entity",
        headers=headers,
        cookies=cookies,
        data=data,
        files=files,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def ensure_followers(user_id: int, need: int) -> None:
    async with async_session_maker() as session:
        current = int(
            await session.scalar(
                text(
                    "SELECT COUNT(*) FROM subscriptions WHERE following_id = :uid"
                ),
                {"uid": user_id},
            )
            or 0
        )
        for i in range(max(0, need - current)):
            uname = f"mp_follower_{user_id}_{i}_{uuid.uuid4().hex[:4]}"
            await session.execute(
                text(
                    "INSERT INTO users (username, hashed_password, verified) "
                    "VALUES (:u, 'x', false)"
                ),
                {"u": uname},
            )
            fid = await session.scalar(
                text("SELECT id FROM users WHERE username = :u"), {"u": uname}
            )
            await session.execute(
                text(
                    "INSERT INTO subscriptions (follower_id, following_id) "
                    "VALUES (:f, :t) "
                    "ON CONFLICT ON CONSTRAINT uq_subscriptions_follower_following "
                    "DO NOTHING"
                ),
                {"f": fid, "t": user_id},
            )
        await session.commit()


async def bump_views(pin_ids: list[int], per_pin: int = 25) -> None:
    async with async_session_maker() as session:
        for pid in pin_ids:
            await session.execute(
                text(
                    "INSERT INTO pin_stats (pin_id, view_count) VALUES (:pid, :v) "
                    "ON CONFLICT (pin_id) DO UPDATE SET view_count = :v"
                ),
                {"pid": pid, "v": per_pin},
            )
        await session.commit()


async def main() -> None:
    accounts = {
        "mp_buyer": "Buyer / viewer — chưa seller",
        "mp_seller_ready": "Đủ N/M/K + method + đã enable seller + 1 pin listed",
        "mp_almost": "Có pin nhưng thiếu followers/views — chưa đủ gate",
    }

    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as client:
        # Buyer
        buyer_user = f"mp_buyer_{SUFFIX}"
        buyer_id, buyer_c = await register_or_login(client, buyer_user)

        # Almost eligible
        almost_user = f"mp_almost_{SUFFIX}"
        almost_id, almost_c = await register_or_login(client, almost_user)
        almost_h = csrf_headers(almost_c)
        almost_pins = []
        for i in range(2):
            almost_pins.append(
                await create_pin(client, almost_c, almost_h, f"almost {i}")
            )

        # Seller ready
        seller_user = f"mp_seller_ready_{SUFFIX}"
        seller_id, seller_c = await register_or_login(client, seller_user)
        seller_h = csrf_headers(seller_c)

        # payment method
        r = await client.post(
            "/marketplace/me/payment-methods",
            headers=seller_h,
            cookies=seller_c,
            json={
                "method_type": "bank",
                "display_name": "Vietcombank",
                "account_identifier": "0123456789",
                "bank_code": "970436",
                "account_holder": "Seller Ready",
            },
        )
        if r.status_code not in (201, 409):
            # may already exist from re-run — ignore if list non-empty
            r2 = await client.get(
                "/marketplace/me/payment-methods",
                headers=seller_h,
                cookies=seller_c,
            )
            assert r2.status_code == 200 and len(r2.json()) >= 1, r.text

        pin_ids = []
        need_pins = max(5, settings.MP_ELIGIBILITY_MIN_PINS)
        # count existing pins
        async with async_session_maker() as session:
            existing = int(
                await session.scalar(
                    text("SELECT COUNT(*) FROM pins WHERE user_id = :u"),
                    {"u": seller_id},
                )
                or 0
            )
        for i in range(max(0, need_pins - existing)):
            pin_ids.append(
                await create_pin(client, seller_c, seller_h, f"seller pin {i}")
            )
        async with async_session_maker() as session:
            rows = (
                await session.execute(
                    text("SELECT id FROM pins WHERE user_id = :u"),
                    {"u": seller_id},
                )
            ).fetchall()
            pin_ids = [r[0] for r in rows]

        await bump_views(pin_ids, per_pin=30)
        await ensure_followers(seller_id, settings.MP_ELIGIBILITY_MIN_FOLLOWERS)

        r = await client.post(
            "/marketplace/me/enable-selling",
            headers=seller_h,
            cookies=seller_c,
        )
        assert r.status_code == 200, r.text

        # list first pin if not listed
        first_pin = pin_ids[0]
        r = await client.get(
            f"/marketplace/pins/{first_pin}/listing",
            headers=seller_h,
            cookies=seller_c,
        )
        if r.status_code == 200 and (r.json() is None or r.json().get("status") != "listed"):
            r = await client.post(
                f"/marketplace/pins/{first_pin}/listing",
                headers=seller_h,
                cookies=seller_c,
                json={"price_minor": 999, "currency": "USD", "attestation_accepted": True},
            )
            assert r.status_code == 201, r.text

    print("=== Marketplace test accounts ===")
    print(f"Password (all): {PASSWORD}")
    print()
    print(f"1) {buyer_user:28}  id={buyer_id}  — {accounts['mp_buyer']}")
    print(f"2) {almost_user:28}  id={almost_id}  — {accounts['mp_almost']}")
    print(f"3) {seller_user:28}  id={seller_id}  — {accounts['mp_seller_ready']}")
    print()
    print(f"Seller listed pin id: {first_pin}  →  /pin/{first_pin}")
    print("FE: http://localhost:3000")


if __name__ == "__main__":
    asyncio.run(main())
