"""Marketplace Sprint4 smoke — orders + SePay mock + grant + idempotent webhook."""
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


async def register_login(client, username: str, *, verified: bool = True):
    r = await client.post("/users/register", json={"username": username, "password": PASSWORD})
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    if verified:
        async with async_session_maker() as session:
            await session.execute(
                text("UPDATE users SET verified = true, email = :e WHERE id = :id"),
                {"e": f"{username}@example.com", "id": uid},
            )
            await session.commit()
    r = await client.post("/users/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return uid, r.cookies


def png() -> bytes:
    img = Image.new("RGB", (140, 110), (20, 90, 150))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def create_pin(client, cookies, headers) -> int:
    r = await client.post(
        "/pins/create-pin-entity",
        headers=headers,
        cookies=cookies,
        data={"pin_model": '{"title":"s4","description":"s4"}'},
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
            uname = f"s4f_{user_id}_{i}_{uuid.uuid4().hex[:4]}"
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
    assert head == "a3b4c5d6e7f8", f"expected a3b4c5d6e7f8 got {head}"
    assert settings.DEV_MODE and settings.MP_SEPAY_MOCK, (
        "smoke requires DEV_MODE=true and MP_SEPAY_MOCK=true"
    )

    suffix = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as client:
        seller_id, seller_cookies = await register_login(client, f"mp4_seller_{suffix}")
        sh = csrf_headers(seller_cookies)

        pin_ids = []
        for _ in range(settings.MP_ELIGIBILITY_MIN_PINS):
            pin_ids.append(await create_pin(client, seller_cookies, sh))
        await force_seller_eligible(seller_id, pin_ids)

        r = await client.post(
            "/marketplace/me/payment-methods",
            headers=sh,
            cookies=seller_cookies,
            json={
                "method_type": "bank",
                "display_name": "Bank",
                "account_identifier": "999",
            },
        )
        assert r.status_code == 201, r.text

        async with async_session_maker() as session:
            await session.execute(
                text(
                    "UPDATE seller_payment_methods SET verification_status='verified', "
                    "verified_at=now(), verified_by='smoke' WHERE user_id = :u"
                ),
                {"u": seller_id},
            )
            await session.commit()

        r = await client.post(
            "/marketplace/me/enable-selling", headers=sh, cookies=seller_cookies
        )
        assert r.status_code == 200, r.text

        listed_pin = pin_ids[0]
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/listing",
            headers=sh,
            cookies=seller_cookies,
            json={"price_minor": 500, "currency": "USD", "attestation_accepted": True},
        )
        assert r.status_code == 201, r.text

        # unverified buyer blocked
        un_id, un_cookies = await register_login(
            client, f"mp4_unv_{suffix}", verified=False
        )
        uh = csrf_headers(un_cookies)
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/orders",
            headers=uh,
            cookies=un_cookies,
        )
        assert r.status_code == 403, r.text
        assert r.json()["detail"] == "email_not_verified"

        # self-buy blocked
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/orders",
            headers=sh,
            cookies=seller_cookies,
        )
        assert r.status_code == 403, r.text
        assert r.json()["detail"] == "cannot_buy_own_pin"

        buyer_id, buyer_cookies = await register_login(client, f"mp4_buyer_{suffix}")
        bh = csrf_headers(buyer_cookies)

        r = await client.post(
            f"/marketplace/pins/{listed_pin}/orders",
            headers=bh,
            cookies=buyer_cookies,
        )
        assert r.status_code == 201, r.text
        order = r.json()["order"]
        assert order["status"] == "pending"
        assert order["charge_amount_vnd"] == max(
            1, int(round(5.0 * float(settings.MP_USD_TO_VND_RATE)))
        )
        order_id = order["id"]
        payment_code = order["payment_code"]

        # reuse pending
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/orders",
            headers=bh,
            cookies=buyer_cookies,
        )
        assert r.status_code == 201, r.text
        assert r.json()["reused"] is True
        assert r.json()["order"]["id"] == order_id

        # mock pay
        r = await client.post(
            f"/marketplace/dev/mock-sepay-paid/{order_id}",
            headers=bh,
            cookies=buyer_cookies,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "paid"

        r = await client.get(
            f"/marketplace/pins/{listed_pin}/purchase-state",
            headers=bh,
            cookies=buyer_cookies,
        )
        assert r.status_code == 200, r.text
        assert r.json()["state"] == "owned"

        # original download for buyer
        r = await client.get(
            f"/pins/original/{listed_pin}",
            headers=bh,
            cookies=buyer_cookies,
        )
        assert r.status_code in (200, 302), r.text

        # already owned
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/orders",
            headers=bh,
            cookies=buyer_cookies,
        )
        assert r.status_code == 409, r.text

        # second buyer + webhook idempotent
        buyer2_id, b2c = await register_login(client, f"mp4_buyer2_{suffix}")
        b2h = csrf_headers(b2c)
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/orders",
            headers=b2h,
            cookies=b2c,
        )
        assert r.status_code == 201, r.text
        o2 = r.json()["order"]
        event_payload = {
            "id": 990001,
            "transferType": "in",
            "transferAmount": o2["charge_amount_vnd"],
            "code": o2["payment_code"],
            "content": o2["payment_code"],
            "gateway": "Vietcombank",
        }
        r = await client.post("/marketplace/webhooks/sepay", json=event_payload)
        assert r.status_code == 200, r.text
        assert r.json().get("success") is True

        r = await client.post("/marketplace/webhooks/sepay", json=event_payload)
        assert r.status_code == 200, r.text

        async with async_session_maker() as session:
            access_count = (
                await session.execute(
                    text(
                        "SELECT count(*) FROM pin_license_access "
                        "WHERE user_id = :u AND pin_id = :p"
                    ),
                    {"u": buyer2_id, "p": listed_pin},
                )
            ).scalar_one()
            events = (
                await session.execute(
                    text(
                        "SELECT count(*) FROM payment_events "
                        "WHERE provider = 'sepay' AND provider_event_id = '990001'"
                    )
                )
            ).scalar_one()
        assert access_count == 1
        assert events == 1

    print("ALL_SMOKE_PASS")
    print(f"alembic_head={head}")
    print(f"payment_code_sample={payment_code}")


if __name__ == "__main__":
    asyncio.run(main())
