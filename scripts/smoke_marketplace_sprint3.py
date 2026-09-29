"""Marketplace Sprint3 smoke — payout methods expand + commission + last-method guard."""
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
PASSWORD = "TestPass123!"


def csrf_headers(cookies: httpx.Cookies) -> dict[str, str]:
    token = cookies.get("csrf_token")
    assert token
    return {"X-CSRF-Token": token}


async def register_login(client, username: str):
    r = await client.post("/users/register", json={"username": username, "password": PASSWORD})
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    r = await client.post("/users/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return uid, r.cookies


def png() -> bytes:
    img = Image.new("RGB", (120, 100), (10, 80, 140))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def create_pin(client, cookies, headers) -> int:
    r = await client.post(
        "/pins/create-pin-entity",
        headers=headers,
        cookies=cookies,
        data={"pin_model": '{"title":"s3","description":"s3"}'},
        files={"file": ("a.png", png(), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def force_seller_eligible(user_id: int, pin_ids: list[int]) -> None:
    async with async_session_maker() as session:
        for pid in pin_ids:
            await session.execute(
                text(
                    "INSERT INTO pin_stats (pin_id, view_count) VALUES (:p, 50) "
                    "ON CONFLICT (pin_id) DO UPDATE SET view_count = 50"
                ),
                {"p": pid},
            )
        for i in range(settings.MP_ELIGIBILITY_MIN_FOLLOWERS):
            uname = f"s3f_{user_id}_{i}_{uuid.uuid4().hex[:4]}"
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


async def main() -> None:
    async with async_session_maker() as session:
        head = (
            await session.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one()
    assert head == "f2a3b4c5d6e7", f"expected f2a3b4c5d6e7 got {head}"

    suffix = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as client:
        uid, cookies = await register_login(client, f"mp3_seller_{suffix}")
        h = csrf_headers(cookies)

        r = await client.get("/marketplace/me/payout-config", headers=h, cookies=cookies)
        assert r.status_code == 200, r.text
        assert "commission_percent" in r.json()

        r = await client.get(
            "/marketplace/me/payout-config",
            headers=h,
            cookies=cookies,
            params={"price_minor": 1000},
        )
        assert r.status_code == 200, r.text
        assert r.json()["seller_net_minor"] is not None

        # first method auto primary
        r = await client.post(
            "/marketplace/me/payment-methods",
            headers=h,
            cookies=cookies,
            json={
                "method_type": "bank",
                "display_name": "Bank A",
                "account_identifier": "111",
                "bank_name": "VCB",
                "account_holder": "Seller A",
            },
        )
        assert r.status_code == 201, r.text
        m1 = r.json()
        assert m1["is_primary"] is True
        assert m1["bank_name"] == "VCB"

        r = await client.post(
            "/marketplace/me/payment-methods",
            headers=h,
            cookies=cookies,
            json={
                "method_type": "e_wallet",
                "display_name": "Wallet B",
                "account_identifier": "222",
                "is_primary": True,
            },
        )
        assert r.status_code == 201, r.text
        m2 = r.json()
        assert m2["is_primary"] is True

        async with async_session_maker() as session:
            await session.execute(
                text(
                    "UPDATE seller_payment_methods SET verification_status='verified', "
                    "verified_at=now(), verified_by='smoke' WHERE user_id = :u"
                ),
                {"u": uid},
            )
            await session.commit()

        r = await client.get("/marketplace/me/payment-methods", headers=h, cookies=cookies)
        methods = r.json()
        primaries = [m for m in methods if m["is_primary"]]
        assert len(primaries) == 1 and primaries[0]["id"] == m2["id"]

        # Make eligible + list a pin
        pin_ids = []
        for _ in range(settings.MP_ELIGIBILITY_MIN_PINS):
            pin_ids.append(await create_pin(client, cookies, h))
        await force_seller_eligible(uid, pin_ids)

        r = await client.post("/marketplace/me/enable-selling", headers=h, cookies=cookies)
        assert r.status_code == 200, r.text

        r = await client.post(
            f"/marketplace/pins/{pin_ids[0]}/listing",
            headers=h,
            cookies=cookies,
            json={"price_minor": 1500, "currency": "USD", "attestation_accepted": True},
        )
        assert r.status_code == 201, r.text

        # Cannot delete last active while listed — deactivate m1 first, then try delete m2
        r = await client.patch(
            f"/marketplace/me/payment-methods/{m1['id']}",
            headers=h,
            cookies=cookies,
            json={"is_active": False},
        )
        assert r.status_code == 200, r.text

        r = await client.delete(
            f"/marketplace/me/payment-methods/{m2['id']}",
            headers=h,
            cookies=cookies,
        )
        assert r.status_code == 403, r.text
        assert r.json()["detail"] == "cannot_remove_last_payout_while_listed"

        r = await client.patch(
            f"/marketplace/me/payment-methods/{m2['id']}",
            headers=h,
            cookies=cookies,
            json={"is_active": False},
        )
        assert r.status_code == 403, r.text

    print("ALL_SMOKE_PASS")
    print(f"alembic_head={head}")


if __name__ == "__main__":
    asyncio.run(main())
