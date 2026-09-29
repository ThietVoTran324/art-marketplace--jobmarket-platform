"""Marketplace Sprint6 smoke — verification_status gate P + admin verify + SePay mock flag."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import io
import json
import time
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
    img = Image.new("RGB", (120, 100), (40, 100, 160))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def create_pin(client, cookies, headers) -> int:
    r = await client.post(
        "/pins/create-pin-entity",
        headers=headers,
        cookies=cookies,
        data={"pin_model": '{"title":"s6","description":"s6"}'},
        files={"file": ("a.png", png(), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def force_nm_k(user_id: int, pin_ids: list[int]) -> None:
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
            uname = f"s6f_{user_id}_{i}_{uuid.uuid4().hex[:4]}"
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


async def main() -> None:
    async with async_session_maker() as session:
        head = (
            await session.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one()
    assert head == "e7f8a9b0c1d2", f"expected e7f8a9b0c1d2 got {head}"
    assert settings.DEV_MODE and settings.MP_SEPAY_MOCK, (
        "smoke requires DEV_MODE=true and MP_SEPAY_MOCK=true"
    )

    suffix = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as client:
        seller_id, seller_c = await register_login(client, f"mp6_seller_{suffix}")
        sh = csrf_headers(seller_c)

        pin_ids = []
        for _ in range(settings.MP_ELIGIBILITY_MIN_PINS):
            pin_ids.append(await create_pin(client, seller_c, sh))
        await force_nm_k(seller_id, pin_ids)

        # Create method → unverified → P fails
        r = await client.post(
            "/marketplace/me/payment-methods",
            headers=sh,
            cookies=seller_c,
            json={
                "method_type": "bank",
                "display_name": "Unverified Bank",
                "account_identifier": "555",
                "bank_name": "VCB",
            },
        )
        assert r.status_code == 201, r.text
        method = r.json()
        assert method["verification_status"] == "unverified"
        method_id = method["id"]

        r = await client.get("/marketplace/me/eligibility", headers=sh, cookies=seller_c)
        assert r.status_code == 200, r.text
        elig = r.json()
        p_crit = next(c for c in elig["criteria"] if c["code"] == "P")
        assert p_crit["passed"] is False, elig
        assert elig["eligible"] is False

        r = await client.post("/marketplace/me/enable-selling", headers=sh, cookies=seller_c)
        assert r.status_code == 400, r.text

        # Admin verify
        admin_id, admin_c = await register_login(client, f"mp6_admin_{suffix}")
        await grant_admin(admin_id)
        r = await client.post(
            "/users/login",
            json={"username": f"mp6_admin_{suffix}", "password": PASSWORD},
        )
        assert r.status_code == 200, r.text
        admin_c = r.cookies
        ah = csrf_headers(admin_c)

        r = await client.patch(
            f"/admin/marketplace/payment-methods/{method_id}",
            headers=ah,
            cookies=admin_c,
            json={"verification_status": "verified"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["verification_status"] == "verified"
        assert r.json()["verified_by"] == f"admin:{admin_id}"

        r = await client.get("/marketplace/me/eligibility", headers=sh, cookies=seller_c)
        elig = r.json()
        p_crit = next(c for c in elig["criteria"] if c["code"] == "P")
        assert p_crit["passed"] is True, elig
        assert elig["eligible"] is True

        r = await client.post("/marketplace/me/enable-selling", headers=sh, cookies=seller_c)
        assert r.status_code == 200, r.text

        listed_pin = pin_ids[0]
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/listing",
            headers=sh,
            cookies=seller_c,
            json={"price_minor": 400, "currency": "USD", "attestation_accepted": True},
        )
        assert r.status_code == 201, r.text

        buyer_id, buyer_c = await register_login(client, f"mp6_buyer_{suffix}")
        bh = csrf_headers(buyer_c)
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/orders",
            headers=bh,
            cookies=buyer_c,
        )
        assert r.status_code == 201, r.text
        order = r.json()["order"]
        order_id = order["id"]
        payment_code = order["payment_code"]

        r = await client.get(
            f"/marketplace/pins/{listed_pin}/purchase-state",
            headers=bh,
            cookies=buyer_c,
        )
        assert r.status_code == 200, r.text
        ps = r.json()
        assert ps["state"] == "pending"
        assert ps["sepay_mock_enabled"] is True

        r = await client.post(
            f"/marketplace/dev/mock-sepay-paid/{order_id}",
            headers=bh,
            cookies=buyer_c,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "paid"

        # Signed webhook idempotency fixture (second order)
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/orders",
            headers=bh,
            cookies=buyer_c,
        )
        # already owned → conflict
        assert r.status_code == 409, r.text

        # New pin for signed webhook path
        pin2 = await create_pin(client, seller_c, sh)
        async with async_session_maker() as session:
            await session.execute(
                text(
                    "INSERT INTO pin_stats (pin_id, view_count) VALUES (:p, 50) "
                    "ON CONFLICT (pin_id) DO UPDATE SET view_count = 50"
                ),
                {"p": pin2},
            )
            await session.commit()
        r = await client.post(
            f"/marketplace/pins/{pin2}/listing",
            headers=sh,
            cookies=seller_c,
            json={"price_minor": 300, "currency": "USD", "attestation_accepted": True},
        )
        assert r.status_code == 201, r.text

        buyer2_id, buyer2_c = await register_login(client, f"mp6_buyer2_{suffix}")
        b2h = csrf_headers(buyer2_c)
        r = await client.post(
            f"/marketplace/pins/{pin2}/orders",
            headers=b2h,
            cookies=buyer2_c,
        )
        assert r.status_code == 201, r.text
        order2 = r.json()["order"]
        payload = {
            "id": int(time.time()) % 10_000_000,
            "transferType": "in",
            "transferAmount": order2["charge_amount_vnd"],
            "code": order2["payment_code"],
            "content": order2["payment_code"],
        }
        raw = json.dumps(payload, separators=(",", ":")).encode()
        secret = settings.MP_SEPAY_WEBHOOK_SECRET or "smoke-secret"
        # If secret unset under mock, unsigned OK; also test signed when secret set via env override
        ts = str(int(time.time()))
        if settings.MP_SEPAY_WEBHOOK_SECRET:
            sig = "sha256=" + hmac.new(
                secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256
            ).hexdigest()
            headers = {
                "Content-Type": "application/json",
                "X-SePay-Signature": sig,
                "X-SePay-Timestamp": ts,
            }
        else:
            headers = {"Content-Type": "application/json"}
        r = await client.post("/marketplace/webhooks/sepay", content=raw, headers=headers)
        assert r.status_code == 200, r.text
        assert r.json().get("success") is True

        r = await client.get(
            f"/marketplace/pins/{pin2}/purchase-state",
            headers=b2h,
            cookies=buyer2_c,
        )
        assert r.json()["state"] == "owned"

        # Cannot unverify last method while listed
        r = await client.patch(
            f"/admin/marketplace/payment-methods/{method_id}",
            headers=ah,
            cookies=admin_c,
            json={"verification_status": "unverified"},
        )
        assert r.status_code == 403, r.text

    print("ALL_SMOKE_PASS")
    print(f"alembic_head={head}")


if __name__ == "__main__":
    asyncio.run(main())
