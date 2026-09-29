"""Marketplace Sprint8 smoke — bank_code, payout execute stub, idempotent, seller 403."""
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


def auth_headers(cookies: httpx.Cookies) -> dict[str, str]:
    token = cookies.get("csrf_token")
    assert token, "missing csrf_token"
    parts = []
    for key in ("access_token", "csrf_token", "refresh_token"):
        val = cookies.get(key)
        if val:
            parts.append(f"{key}={val}")
    return {"X-CSRF-Token": token, "Cookie": "; ".join(parts)}


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
    img = Image.new("RGB", (120, 90), (20, 90, 160))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def create_pin(client, headers) -> int:
    r = await client.post(
        "/pins/create-pin-entity",
        headers=headers,
        data={"pin_model": '{"title":"s8","description":"s8"}'},
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
            uname = f"s8f_{user_id}_{i}_{uuid.uuid4().hex[:4]}"
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


async def grant_admin(user_id: int) -> None:
    async with async_session_maker() as session:
        await session.execute(
            text(
                "INSERT INTO user_roles (user_id, role) VALUES (:u, 'admin') "
                "ON CONFLICT DO NOTHING"
            ),
            {"u": user_id},
        )
        await session.commit()


async def force_order_paid(order_id: int) -> None:
    from app.api.rest.marketplace.orders import mark_order_paid
    from app.postgresql.models import PinOrdersOrm

    async with async_session_maker() as session:
        order = await session.get(PinOrdersOrm, order_id)
        assert order is not None
        await mark_order_paid(
            session,
            order,
            provider_event_id=f"smoke8-{order_id}-{uuid.uuid4().hex[:6]}",
            payload={"smoke": True},
        )
        await session.commit()


async def main() -> None:
    async with async_session_maker() as session:
        head = (
            await session.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one()
    assert head == "b0c1d2e3f4a5", f"expected b0c1d2e3f4a5 got {head}"

    suffix = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as client:
        seller_id, seller_c = await register_login(client, f"mp8_seller_{suffix}")
        sh = auth_headers(seller_c)

        # AC-01: bank without code/holder rejected
        r = await client.post(
            "/marketplace/me/payment-methods",
            headers=sh,
            json={
                "method_type": "bank",
                "display_name": "Bad",
                "account_identifier": "1",
            },
        )
        assert r.status_code == 400, r.text

        pin_ids = []
        for _ in range(settings.MP_ELIGIBILITY_MIN_PINS):
            pin_ids.append(await create_pin(client, sh))
        await force_seller_eligible(seller_id, pin_ids)

        r = await client.post(
            "/marketplace/me/payment-methods",
            headers=sh,
            json={
                "method_type": "bank",
                "display_name": "Vietin",
                "account_identifier": "0123456789",
                "bank_code": "970415",
                "account_holder": "Seller Smoke",
                "is_primary": True,
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["bank_code"] == "970415"

        async with async_session_maker() as session:
            await session.execute(
                text(
                    "UPDATE seller_payment_methods SET verification_status='verified', "
                    "verified_at=now(), verified_by='smoke' WHERE user_id = :u"
                ),
                {"u": seller_id},
            )
            await session.commit()

        r = await client.post("/marketplace/me/enable-selling", headers=sh)
        assert r.status_code == 200, r.text

        listed = pin_ids[0]
        r = await client.post(
            f"/marketplace/pins/{listed}/listing",
            headers=sh,
            json={
                "price_minor": 800,
                "currency": "USD",
                "attestation_accepted": True,
            },
        )
        assert r.status_code == 201, r.text

        buyer_id, buyer_c = await register_login(client, f"mp8_buyer_{suffix}")
        bh = auth_headers(buyer_c)
        r = await client.post(f"/marketplace/pins/{listed}/orders", headers=bh)
        assert r.status_code == 201, r.text
        order_id = r.json()["order"]["id"]

        await force_order_paid(order_id)

        # Snapshot has bank_code
        async with async_session_maker() as session:
            row = (
                await session.execute(
                    text(
                        "SELECT payout_status, payout_bank_code, payout_amount_vnd "
                        "FROM pin_orders WHERE id = :id"
                    ),
                    {"id": order_id},
                )
            ).one()
        assert row[0] == "pending", row
        assert row[1] == "970415", row
        assert row[2] and row[2] > 0, row

        # Seller cannot execute
        r = await client.post(
            f"/admin/marketplace/payouts/{order_id}/execute",
            headers=sh,
            json={},
        )
        assert r.status_code == 403, r.text

        admin_id, admin_c = await register_login(client, f"mp8_admin_{suffix}")
        await grant_admin(admin_id)
        r = await client.post(
            "/users/login",
            json={"username": f"mp8_admin_{suffix}", "password": PASSWORD},
        )
        assert r.status_code == 200, r.text
        ah = auth_headers(r.cookies)

        r = await client.get("/admin/marketplace/payouts/pending", headers=ah)
        assert r.status_code == 200, r.text
        assert any(x["order_id"] == order_id for x in r.json()), r.text

        # force_fail then retry success
        r = await client.post(
            f"/admin/marketplace/payouts/{order_id}/execute",
            headers=ah,
            json={"force_fail": True, "note": "smoke fail"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["payout_status"] == "failed"

        r = await client.post(
            f"/admin/marketplace/payouts/{order_id}/execute",
            headers=ah,
            json={"note": "smoke ok"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["payout_status"] == "paid"

        # idempotent
        r = await client.post(
            f"/admin/marketplace/payouts/{order_id}/execute",
            headers=ah,
            json={},
        )
        assert r.status_code == 409, r.text
        assert r.json()["detail"] == "already_paid_out"

        r = await client.get("/marketplace/me/payouts", headers=sh)
        assert r.status_code == 200, r.text
        mine = [x for x in r.json() if x["order_id"] == order_id]
        assert mine and mine[0]["payout_status"] == "paid"

        async with async_session_maker() as session:
            n = (
                await session.execute(
                    text(
                        "SELECT COUNT(*) FROM payout_attempts WHERE order_id = :o"
                    ),
                    {"o": order_id},
                )
            ).scalar_one()
        assert n >= 3, n  # started/fail paths + success

        # open_api provider never HTTP — raises NotConfigured in-process
        from app.api.rest.marketplace.payout_providers import (
            OpenApiPayoutProvider,
            PayoutNotConfigured,
            PayoutTransferRequest,
        )

        try:
            OpenApiPayoutProvider().transfer(
                PayoutTransferRequest(
                    order_id=order_id,
                    amount_vnd=1000,
                    account_identifier="1",
                    account_holder="x",
                    bank_code="970415",
                    bank_name="VietinBank",
                    method_type="bank",
                    idempotency_key="t",
                )
            )
            raise AssertionError("open_api should not succeed")
        except PayoutNotConfigured:
            pass

    print("ALL_SMOKE_PASS")
    print(f"alembic_head={head} order_id={order_id}")


if __name__ == "__main__":
    asyncio.run(main())
