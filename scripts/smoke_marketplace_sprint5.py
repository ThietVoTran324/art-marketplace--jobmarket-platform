"""Marketplace Sprint5 smoke — attestation, hash, copyright report, certificate."""
from __future__ import annotations

import asyncio
import io
import uuid

import httpx
from PIL import Image
from sqlalchemy import text

from app.celery.tasks import generate_pin_preview
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
    img = Image.new("RGB", (130, 100), (40, 100, 160))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def create_pin(client, cookies, headers) -> int:
    r = await client.post(
        "/pins/create-pin-entity",
        headers=headers,
        cookies=cookies,
        data={"pin_model": '{"title":"s5","description":"s5"}'},
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
            uname = f"s5f_{user_id}_{i}_{uuid.uuid4().hex[:4]}"
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
    assert head == "b4c5d6e7f8a9", f"expected b4c5d6e7f8a9 got {head}"
    assert settings.DEV_MODE and settings.MP_SEPAY_MOCK, (
        "smoke requires DEV_MODE=true and MP_SEPAY_MOCK=true"
    )

    suffix = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as client:
        seller_id, seller_cookies = await register_login(client, f"mp5_seller_{suffix}")
        sh = csrf_headers(seller_cookies)

        pin_ids = []
        for _ in range(settings.MP_ELIGIBILITY_MIN_PINS):
            pin_ids.append(await create_pin(client, seller_cookies, sh))
        listed_pin = pin_ids[0]
        generate_pin_preview.run(listed_pin)

        async with async_session_maker() as session:
            sha = (
                await session.execute(
                    text("SELECT content_sha256 FROM pins WHERE id = :p"),
                    {"p": listed_pin},
                )
            ).scalar_one()
        assert sha and len(sha) == 64

        await force_seller_eligible(seller_id, pin_ids)
        r = await client.post(
            "/marketplace/me/payment-methods",
            headers=sh,
            cookies=seller_cookies,
            json={
                "method_type": "bank",
                "display_name": "Bank",
                "account_identifier": "111",
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

        # attestation required
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/listing",
            headers=sh,
            cookies=seller_cookies,
            json={"price_minor": 700, "currency": "USD"},
        )
        assert r.status_code == 400, r.text
        assert r.json()["detail"] == "attestation_required"

        r = await client.post(
            f"/marketplace/pins/{listed_pin}/listing",
            headers=sh,
            cookies=seller_cookies,
            json={
                "price_minor": 700,
                "currency": "USD",
                "attestation_accepted": True,
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["attestation_accepted"] is True
        assert r.json()["attestation_version"] == settings.MP_ATTESTATION_VERSION

        # copyright report
        reporter_id, rc = await register_login(client, f"mp5_rep_{suffix}")
        rh = csrf_headers(rc)
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/copyright-reports",
            headers=rh,
            cookies=rc,
            json={"reason": "This pin uses my photo without permission"},
        )
        assert r.status_code == 201, r.text
        report_id = r.json()["id"]

        admin_id, ac = await register_login(client, f"mp5_admin_{suffix}")
        await grant_admin(admin_id)
        # re-login so JWT/roles refresh if needed — roles checked from DB
        r = await client.post(
            "/users/login",
            json={"username": f"mp5_admin_{suffix}", "password": PASSWORD},
        )
        assert r.status_code == 200, r.text
        ac = r.cookies
        ah = csrf_headers(ac)

        r = await client.get(
            "/admin/copyright-reports",
            headers=ah,
            cookies=ac,
            params={"status": "open"},
        )
        assert r.status_code == 200, r.text
        assert any(x["id"] == report_id for x in r.json())

        r = await client.patch(
            f"/admin/copyright-reports/{report_id}",
            headers=ah,
            cookies=ac,
            json={"status": "dismissed", "admin_note": "not actionable"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "dismissed"

        # buy + certificate
        buyer_id, bc = await register_login(client, f"mp5_buyer_{suffix}")
        bh = csrf_headers(bc)
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/orders",
            headers=bh,
            cookies=bc,
        )
        assert r.status_code == 201, r.text
        order_id = r.json()["order"]["id"]
        r = await client.post(
            f"/marketplace/dev/mock-sepay-paid/{order_id}",
            headers=bh,
            cookies=bc,
        )
        assert r.status_code == 200, r.text

        r = await client.get(
            f"/marketplace/me/certificates/{order_id}",
            headers=bh,
            cookies=bc,
        )
        assert r.status_code == 200, r.text
        cert = r.json()
        assert cert["order_id"] == order_id
        assert cert["content_sha256"] == sha
        assert cert["certificate_code"].startswith("LC")

        r = await client.get(
            f"/marketplace/me/certificates/by-pin/{listed_pin}",
            headers=bh,
            cookies=bc,
        )
        assert r.status_code == 200, r.text
        assert r.json()["id"] == cert["id"]

    print("ALL_SMOKE_PASS")
    print(f"alembic_head={head}")
    print(f"certificate_code={cert['certificate_code']}")


if __name__ == "__main__":
    asyncio.run(main())
