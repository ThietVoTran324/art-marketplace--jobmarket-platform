"""Marketplace Sprint7 smoke — watermark evidence, list gate, PinOut strip, access audit."""
from __future__ import annotations

import asyncio
import io
import uuid
from pathlib import Path

import httpx
from PIL import Image
from sqlalchemy import text

from app.api.rest.pins.watermark import EVIDENCE_TEXT
from app.config import settings
from app.postgresql.database import async_session_maker

BASE = "http://127.0.0.1:8000"
PASSWORD = "TestPass123!"


def auth_headers(cookies: httpx.Cookies) -> dict[str, str]:
    """Build CSRF + Cookie headers.

    When DEV_MODE=false, auth cookies are Secure; httpx will not attach them on
    plain http://127.0.0.1 — so we set Cookie explicitly for in-container smoke.
    """
    token = cookies.get("csrf_token")
    assert token, "missing csrf_token cookie"
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


def png(color=(30, 140, 200)) -> bytes:
    img = Image.new("RGB", (320, 240), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def create_pin(client, cookies, headers) -> dict:
    r = await client.post(
        "/pins/create-pin-entity",
        headers=headers,
        data={"pin_model": '{"title":"s7","description":"s7"}'},
        files={"file": ("a.png", png(), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()


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
            uname = f"s7f_{user_id}_{i}_{uuid.uuid4().hex[:4]}"
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
    assert head == "a9b0c1d2e3f4", f"expected a9b0c1d2e3f4 got {head}"

    suffix = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as client:
        seller_id, seller_cookies = await register_login(client, f"mp7_seller_{suffix}")
        sh = auth_headers(seller_cookies)

        pin_ids: list[int] = []
        first_pin: dict | None = None
        for _ in range(settings.MP_ELIGIBILITY_MIN_PINS):
            pin = await create_pin(client, seller_cookies, sh)
            pin_ids.append(pin["id"])
            if first_pin is None:
                first_pin = pin
        assert first_pin is not None
        listed_pin = pin_ids[0]

        # AC-03: strip original_image; expose has_original
        assert "original_image" not in first_pin, first_pin
        assert first_pin.get("has_original") is True, first_pin
        assert first_pin.get("image", "").startswith("pins/preview/"), first_pin

        # Clean preview on upload (no watermark until listed)
        assert EVIDENCE_TEXT == "just buy it"
        preview_path = Path(settings.MEDIA_PATH) / first_pin["image"]
        assert preview_path.is_file(), preview_path
        with Image.open(preview_path) as img:
            assert img.format == "JPEG"
            clean = img.convert("RGB")
            clean_mid = clean.crop(
                (
                    clean.width // 4,
                    clean.height // 4,
                    (clean.width * 3) // 4,
                    (clean.height * 3) // 4,
                )
            )
            clean_pixels = list(clean_mid.getdata())
            clean_uniq = len({p for p in clean_pixels[:: max(1, len(clean_pixels) // 200)]})
        assert clean_uniq <= 4, f"upload preview should be clean, uniq={clean_uniq}"

        async with async_session_maker() as session:
            row = (
                await session.execute(
                    text(
                        "SELECT original_image, content_sha256 FROM pins WHERE id = :p"
                    ),
                    {"p": listed_pin},
                )
            ).one()
        original_rel, sha = row
        assert sha and len(sha) == 64
        original_path = Path(settings.MEDIA_PATH) / original_rel
        assert original_path.read_bytes() != preview_path.read_bytes()

        await force_seller_eligible(seller_id, pin_ids)
        r = await client.post(
            "/marketplace/me/payment-methods",
            headers=sh,
            json={
                "method_type": "bank",
                "display_name": "Bank",
                "account_identifier": "111",
                "bank_code": "970415",
                "account_holder": "Smoke Seller",
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
        r = await client.post("/marketplace/me/enable-selling", headers=sh)
        assert r.status_code == 200, r.text

        # List OK when media ready
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/listing",
            headers=sh,
            json={
                "price_minor": 700,
                "currency": "USD",
                "attestation_accepted": True,
            },
        )
        assert r.status_code == 201, r.text

        # After list → soft diagonal watermark appears
        async with async_session_maker() as session:
            listed_image = (
                await session.execute(
                    text("SELECT image FROM pins WHERE id = :p"),
                    {"p": listed_pin},
                )
            ).scalar_one()
        with Image.open(Path(settings.MEDIA_PATH) / listed_image) as img:
            wm = img.convert("RGB")
            wm_mid = wm.crop(
                (
                    wm.width // 4,
                    wm.height // 4,
                    (wm.width * 3) // 4,
                    (wm.height * 3) // 4,
                )
            )
            wm_pixels = list(wm_mid.getdata())
            wm_uniq = len({p for p in wm_pixels[:: max(1, len(wm_pixels) // 200)]})
        assert wm_uniq > clean_uniq, f"listed preview should be watermarked, uniq={wm_uniq}"

        # Gate: missing preview → pin_media_incomplete
        async with async_session_maker() as session:
            await session.execute(
                text("UPDATE pins SET image = NULL WHERE id = :id"),
                {"id": listed_pin},
            )
            await session.commit()
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/listing",
            headers=sh,
            json={
                "price_minor": 700,
                "currency": "USD",
                "attestation_accepted": True,
            },
        )
        assert r.status_code == 400, r.text
        assert r.json()["detail"] == "pin_media_incomplete"

        # Gate: missing hash → pin_hash_missing
        async with async_session_maker() as session:
            await session.execute(
                text(
                    "UPDATE pins SET image = :img, content_sha256 = NULL WHERE id = :id"
                ),
                {"img": first_pin["image"], "id": listed_pin},
            )
            await session.commit()
        r = await client.post(
            f"/marketplace/pins/{listed_pin}/listing",
            headers=sh,
            json={
                "price_minor": 700,
                "currency": "USD",
                "attestation_accepted": True,
            },
        )
        assert r.status_code == 400, r.text
        assert r.json()["detail"] == "pin_hash_missing"

        async with async_session_maker() as session:
            await session.execute(
                text("UPDATE pins SET content_sha256 = :h WHERE id = :id"),
                {"h": sha, "id": listed_pin},
            )
            await session.commit()

        # Audit mint + file
        r = await client.get(f"/pins/original/{listed_pin}", headers=sh)
        assert r.status_code == 200, r.text
        signed = r.json()["url"]
        r = await client.get(signed, headers=sh)
        assert r.status_code == 200, r.text

        async with async_session_maker() as session:
            actions = (
                await session.execute(
                    text(
                        "SELECT action FROM pin_original_access_logs "
                        "WHERE pin_id = :p AND user_id = :u ORDER BY id"
                    ),
                    {"p": listed_pin, "u": seller_id},
                )
            ).scalars().all()
        assert "mint" in actions, actions
        assert "file" in actions, actions

    print("ALL_SMOKE_PASS")
    print(f"alembic_head={head} pin_id={listed_pin}")


if __name__ == "__main__":
    asyncio.run(main())
