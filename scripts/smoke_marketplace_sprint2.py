"""Marketplace Sprint2 smoke — eligibility, seller role, listings, payment methods."""
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
    assert token, "missing csrf_token cookie"
    return {"X-CSRF-Token": token}


async def register_and_login(client: httpx.AsyncClient, username: str) -> tuple[int, httpx.Cookies]:
    r = await client.post(
        "/users/register", json={"username": username, "password": PASSWORD}
    )
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    r = await client.post(
        "/users/login", json={"username": username, "password": PASSWORD}
    )
    assert r.status_code == 200, r.text
    return uid, r.cookies


async def alembic_head() -> str:
    async with async_session_maker() as session:
        return (
            await session.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one()


def make_png_bytes(color=(40, 90, 160)) -> bytes:
    img = Image.new("RGB", (200, 160), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def create_pin_with_media(client, cookies, headers, title: str) -> int:
    files = {"file": ("p.png", make_png_bytes(), "image/png")}
    data = {"pin_model": f'{{"title":"{title}","description":"s2"}}'}
    r = await client.post(
        "/pins/create-pin-entity",
        headers=headers,
        cookies=cookies,
        data=data,
        files=files,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def bump_eligibility(user_id: int, pin_ids: list[int]) -> None:
    """Force N/M/K over thresholds for smoke (views + fake followers)."""
    async with async_session_maker() as session:
        for pid in pin_ids:
            await session.execute(
                text(
                    "INSERT INTO pin_stats (pin_id, view_count) VALUES (:pid, 30) "
                    "ON CONFLICT (pin_id) DO UPDATE SET view_count = 30"
                ),
                {"pid": pid},
            )
        # Need K>=10 followers: create 10 users who follow seller — expensive.
        # Instead lower thresholds temporarily via direct SQL counts:
        # Create 10 follower rows from existing users or insert synthetic users.
        for i in range(10):
            uname = f"mp2_f_{user_id}_{i}_{uuid.uuid4().hex[:4]}"
            await session.execute(
                text(
                    "INSERT INTO users (username, hashed_password, verified) "
                    "VALUES (:u, 'x', false) RETURNING id"
                ),
                {"u": uname},
            )
            fid = (
                await session.execute(text("SELECT id FROM users WHERE username = :u"), {"u": uname})
            ).scalar_one()
            await session.execute(
                text(
                    "INSERT INTO subscriptions (follower_id, following_id) "
                    "VALUES (:f, :t) "
                    "ON CONFLICT ON CONSTRAINT uq_subscriptions_follower_following DO NOTHING"
                ),
                {"f": fid, "t": user_id},
            )
        await session.commit()


async def main() -> None:
    head = await alembic_head()
    assert head == "e1f2a3b4c5d6", f"expected e1f2a3b4c5d6, got {head}"

    # Use low thresholds if defaults too high for quick pin create — smoke will
    # create 5 pins + bump views + followers.
    min_pins = settings.MP_ELIGIBILITY_MIN_PINS
    assert min_pins >= 1

    suffix = uuid.uuid4().hex[:8]
    seller_name = f"mp2_seller_{suffix}"
    other_name = f"mp2_other_{suffix}"

    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as client:
        seller_id, seller_c = await register_and_login(client, seller_name)
        other_id, other_c = await register_and_login(client, other_name)
        seller_h = csrf_headers(seller_c)
        other_h = csrf_headers(other_c)

        # Under threshold: enable fails
        r = await client.post(
            "/marketplace/me/enable-selling", headers=seller_h, cookies=seller_c
        )
        assert r.status_code == 400, r.text

        # Add payment method (P)
        r = await client.post(
            "/marketplace/me/payment-methods",
            headers=seller_h,
            cookies=seller_c,
            json={
                "method_type": "bank",
                "display_name": "Test Bank",
                "account_identifier": "1234567890",
            },
        )
        assert r.status_code == 201, r.text
        method_id = r.json()["id"]
        assert r.json().get("verification_status", "unverified") == "unverified"

        async with async_session_maker() as session:
            await session.execute(
                text(
                    "UPDATE seller_payment_methods SET verification_status='verified', "
                    "verified_at=now(), verified_by='smoke' WHERE id = :id"
                ),
                {"id": method_id},
            )
            await session.commit()

        pin_ids = []
        for i in range(min_pins):
            pid = await create_pin_with_media(
                client, seller_c, seller_h, f"mp2 pin {i}"
            )
            pin_ids.append(pid)

        await bump_eligibility(seller_id, pin_ids)

        r = await client.get(
            "/marketplace/me/eligibility", headers=seller_h, cookies=seller_c
        )
        assert r.status_code == 200, r.text
        elig = r.json()
        assert elig["eligible"] is True, elig

        r = await client.post(
            "/marketplace/me/enable-selling", headers=seller_h, cookies=seller_c
        )
        assert r.status_code == 200, r.text
        assert "seller" in r.json()["roles"]

        pin_id = pin_ids[0]
        r = await client.post(
            f"/marketplace/pins/{pin_id}/listing",
            headers=seller_h,
            cookies=seller_c,
            json={"price_minor": 999, "currency": "USD", "attestation_accepted": True},
        )
        assert r.status_code == 201, r.text
        listing = r.json()
        assert listing["status"] == "listed"
        assert listing["price_minor"] == 999
        listing_id = listing["id"]

        # Non-owner cannot list seller's pin
        r = await client.post(
            f"/marketplace/pins/{pin_id}/listing",
            headers=other_h,
            cookies=other_c,
            json={"price_minor": 100, "currency": "USD", "attestation_accepted": True},
        )
        assert r.status_code == 403, r.text

        # Public listing visible
        r = await client.get(
            f"/marketplace/pins/{pin_id}/listing",
            headers=other_h,
            cookies=other_c,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "listed"

        # Drop below threshold: delete payment method → block new listing
        r = await client.delete(
            f"/marketplace/me/payment-methods/{method_id}",
            headers=seller_h,
            cookies=seller_c,
        )
        assert r.status_code == 204, r.text

        other_pin = pin_ids[1] if len(pin_ids) > 1 else pin_ids[0]
        # Unlist first listing then try re-list while below threshold
        r = await client.patch(
            f"/marketplace/listings/{listing_id}",
            headers=seller_h,
            cookies=seller_c,
            json={"status": "unlisted"},
        )
        assert r.status_code == 200, r.text

        r = await client.post(
            f"/marketplace/pins/{other_pin}/listing",
            headers=seller_h,
            cookies=seller_c,
            json={"price_minor": 500, "currency": "USD", "attestation_accepted": True},
        )
        assert r.status_code == 403, r.text
        assert r.json()["detail"] == "listing_blocked_below_threshold"

        # Seller role still present
        r = await client.get("/users/me/roles", headers=seller_h, cookies=seller_c)
        assert r.status_code == 200, r.text
        role_list = r.json()["roles"]
        assert "seller" in role_list

    print("ALL_SMOKE_PASS")
    print(f"alembic_head={head} seller_id={seller_id} pin_id={pin_id}")


if __name__ == "__main__":
    asyncio.run(main())
