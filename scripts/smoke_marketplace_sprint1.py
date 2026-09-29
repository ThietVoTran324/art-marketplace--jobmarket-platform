"""Marketplace Sprint1 smoke — preview/original ACL + signed URL + license access stub."""
from __future__ import annotations

import asyncio
import io
import uuid
from pathlib import Path

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
        row = await session.execute(text("SELECT version_num FROM alembic_version"))
        return row.scalar_one()


def make_png_bytes(color: tuple[int, int, int] = (20, 120, 200)) -> bytes:
    img = Image.new("RGB", (240, 180), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def grant_access(user_id: int, pin_id: int) -> None:
    async with async_session_maker() as session:
        await session.execute(
            text(
                "INSERT INTO pin_license_access (user_id, pin_id) "
                "VALUES (:uid, :pid) ON CONFLICT DO NOTHING"
            ),
            {"uid": user_id, "pid": pin_id},
        )
        await session.commit()


async def main() -> None:
    head = await alembic_head()
    assert head == "d0e1f2a3b4c5", f"expected alembic d0e1f2a3b4c5, got {head}"

    suffix = uuid.uuid4().hex[:8]
    owner_name = f"mp1_owner_{suffix}"
    other_name = f"mp1_other_{suffix}"
    buyer_name = f"mp1_buyer_{suffix}"

    png = make_png_bytes()

    async with httpx.AsyncClient(base_url=BASE, timeout=90.0) as client:
        owner_id, owner_c = await register_and_login(client, owner_name)
        other_id, other_c = await register_and_login(client, other_name)
        buyer_id, buyer_c = await register_and_login(client, buyer_name)
        owner_h = csrf_headers(owner_c)
        other_h = csrf_headers(other_c)
        buyer_h = csrf_headers(buyer_c)

        files = {"file": ("smoke.png", png, "image/png")}
        data = {"pin_model": '{"title":"mp1 smoke","description":"media"}'}
        r = await client.post(
            "/pins/create-pin-entity",
            headers=owner_h,
            cookies=owner_c,
            data=data,
            files=files,
        )
        assert r.status_code == 201, r.text
        pin = r.json()
        pin_id = pin["id"]
        assert pin.get("has_original") is True, pin
        assert "original_image" not in pin, pin
        assert pin.get("image"), f"preview missing: {pin}"
        assert pin["image"].startswith("pins/preview/"), pin["image"]

        async with async_session_maker() as session:
            row = await session.execute(
                text("SELECT original_image FROM pins WHERE id = :id"),
                {"id": pin_id},
            )
            original_rel = row.scalar_one()
        assert original_rel and original_rel.startswith("pins/original/"), original_rel

        media_root = Path(settings.MEDIA_PATH)
        original_path = media_root / original_rel
        preview_path = media_root / pin["image"]
        assert original_path.is_file(), original_path
        assert preview_path.is_file(), preview_path
        original_bytes = original_path.read_bytes()
        preview_bytes = preview_path.read_bytes()
        assert original_bytes != preview_bytes, "preview must differ from original"

        # Preview endpoint for non-owner
        r = await client.get(
            f"/pins/upload/{pin_id}", headers=other_h, cookies=other_c
        )
        assert r.status_code == 200, r.text
        assert r.content == preview_bytes

        # Non-owner original forbidden
        r = await client.get(
            f"/pins/original/{pin_id}", headers=other_h, cookies=other_c
        )
        assert r.status_code == 403, r.text

        # Owner signed URL + file
        r = await client.get(
            f"/pins/original/{pin_id}", headers=owner_h, cookies=owner_c
        )
        assert r.status_code == 200, r.text
        signed = r.json()["url"]
        assert "sig=" in signed and "exp=" in signed
        r = await client.get(signed, headers=owner_h, cookies=owner_c)
        assert r.status_code == 200, r.text
        assert r.content == original_bytes

        # Expired / bad sig
        r = await client.get(
            f"/pins/original/{pin_id}/file?exp=1&uid={owner_id}&sig=deadbeef",
            headers=owner_h,
            cookies=owner_c,
        )
        assert r.status_code == 403, r.text

        # Buyer with license access stub
        r = await client.get(
            f"/pins/original/{pin_id}", headers=buyer_h, cookies=buyer_c
        )
        assert r.status_code == 403, r.text
        await grant_access(buyer_id, pin_id)
        r = await client.get(
            f"/pins/original/{pin_id}", headers=buyer_h, cookies=buyer_c
        )
        assert r.status_code == 200, r.text
        r = await client.get(r.json()["url"], headers=buyer_h, cookies=buyer_c)
        assert r.status_code == 200, r.text
        assert r.content == original_bytes

    print("ALL_SMOKE_PASS")
    print(f"alembic_head={head} pin_id={pin_id}")


if __name__ == "__main__":
    asyncio.run(main())
