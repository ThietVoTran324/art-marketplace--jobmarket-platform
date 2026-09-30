"""Seed feed pins from Pexels by category/tag (soft-live demo).

Rules (CHỐT):
- 10 random categories × 10 images = 100 pins
- Reuse existing tags (case-insensitive); create if missing
- Authors: all non-admin, non-organization users
- ~25 pins assigned to sellers → always listed ($1–$10 USD)
- ~75 pins assigned to non-seller authors → not listed
- Idempotent: skip if title `[pexels-seed] … #{pexels_id}` already exists
- `--force` ignores the “batch already complete” early exit (still skips dup pexels ids)

Env:
  PEXELS_API_KEY  (required)

Usage:
  docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec -T \
    -e PEXELS_API_KEY -w /fastapi -e PYTHONPATH=/fastapi fastapi-app \
    python -m scripts.seed_pexels_feed

  # force another pass (only adds missing pexels ids / new category rolls):
  ... python -m scripts.seed_pexels_feed --force
"""
from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.rest.job_market.helpers import is_organization_user
from app.api.rest.pins.watermark import original_dir
from app.api.rest.roles import get_user_roles
from app.celery.tasks import generate_pin_preview
from app.config import settings
from app.postgresql.database import async_session_maker
from app.postgresql.models import (
    PinListingsOrm,
    PinStatsOrm,
    PinsOrm,
    TagsOrm,
    UsersOrm,
    pins_tags,
)

MARKER = "[pexels-seed]"
CATEGORIES = 10
PER_CATEGORY = 10
SELLER_SHARE = 0.25  # ~25 of 100 → sellers (listed)
CATEGORY_POOL = [
    "watercolor",
    "oil painting",
    "digital art",
    "portrait photography",
    "landscape photography",
    "abstract art",
    "sculpture",
    "illustration",
    "street art",
    "architecture",
    "fashion photography",
    "minimalism",
    "surreal art",
    "nature photography",
    "calligraphy",
    "ceramic art",
    "graffiti",
    "collage art",
    "vintage photography",
    "floral art",
]


def _api_key() -> str:
    key = (os.getenv("PEXELS_API_KEY") or "").strip()
    if not key:
        print("ERROR: set PEXELS_API_KEY in env", file=sys.stderr)
        sys.exit(1)
    return key


def _http_json(url: str, *, headers: dict[str, str] | None = None) -> dict:
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=60) as resp:
        import json

        return json.loads(resp.read().decode("utf-8"))


def _http_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "pinterest-seed/1.0"})
    with urlopen(req, timeout=120) as resp:
        return resp.read()


def pexels_search(query: str, *, per_page: int, api_key: str) -> list[dict]:
    url = (
        "https://api.pexels.com/v1/search"
        f"?query={quote_plus(query)}&per_page={per_page}&orientation=portrait"
    )
    try:
        data = _http_json(url, headers={"Authorization": api_key})
    except HTTPError as e:
        print(f"Pexels search failed for {query!r}: {e}", file=sys.stderr)
        raise
    except URLError as e:
        print(f"Pexels network error for {query!r}: {e}", file=sys.stderr)
        raise
    return list(data.get("photos") or [])


def pin_title(category: str, pexels_id: int) -> str:
    return f"{MARKER} {category} #{pexels_id}"


async def ensure_tag(session, name: str) -> TagsOrm:
    existing = await session.scalar(
        select(TagsOrm).where(func.lower(TagsOrm.name) == name.lower())
    )
    if existing is not None:
        return existing
    tag = TagsOrm(name=name)
    session.add(tag)
    await session.flush()
    print(f"  + tag created: {name}")
    return tag


async def load_authors(session) -> tuple[list[UsersOrm], list[UsersOrm]]:
    """Return (sellers, non_sellers) — both non-admin and non-org."""
    users = list((await session.scalars(select(UsersOrm).order_by(UsersOrm.id))).all())
    sellers: list[UsersOrm] = []
    others: list[UsersOrm] = []
    for u in users:
        roles = await get_user_roles(session, u.id)
        if "admin" in roles:
            continue
        if await is_organization_user(session, u.id):
            continue
        if "seller" in roles:
            sellers.append(u)
        else:
            others.append(u)
    return sellers, others


async def ensure_seller_listable(session, user: UsersOrm) -> None:
    """Bump pin_stats views so marketplace M gate passes (N/K/P already OK on VPS)."""
    min_n = settings.MP_ELIGIBILITY_MIN_PINS
    min_m = settings.MP_ELIGIBILITY_MIN_VIEWS

    pin_ids = list(
        (await session.scalars(select(PinsOrm.id).where(PinsOrm.user_id == user.id))).all()
    )
    # Placeholder pins without media only if still below N (should not happen for USER01).
    while len(pin_ids) < min_n:
        stub = PinsOrm(
            user_id=user.id,
            title=f"{MARKER} eligibility-stub {len(pin_ids)+1}",
            description="eligibility stub",
        )
        session.add(stub)
        await session.flush()
        session.add(PinStatsOrm(pin_id=stub.id, view_count=0))
        pin_ids.append(stub.id)

    total_views = int(
        await session.scalar(
            select(func.coalesce(func.sum(PinStatsOrm.view_count), 0))
            .select_from(PinStatsOrm)
            .join(PinsOrm, PinsOrm.id == PinStatsOrm.pin_id)
            .where(PinsOrm.user_id == user.id)
        )
        or 0
    )
    if total_views >= min_m:
        return

    need = min_m - total_views
    # Dump remaining views onto first pin for simplicity.
    first_id = pin_ids[0]
    stats = await session.get(PinStatsOrm, first_id)
    if stats is None:
        session.add(PinStatsOrm(pin_id=first_id, view_count=need))
    else:
        stats.view_count = int(stats.view_count or 0) + need
    print(f"  bumped views for {user.username}: +{need} (target M>={min_m})")


async def list_pin(session, pin: PinsOrm, seller: UsersOrm) -> None:
    price_minor = random.randint(100, 1000)  # $1.00 – $10.00
    now = datetime.now(timezone.utc)
    existing = await session.scalar(
        select(PinListingsOrm).where(PinListingsOrm.pin_id == pin.id)
    )
    attest = {
        "attestation_accepted": True,
        "attestation_version": settings.MP_ATTESTATION_VERSION,
        "attested_at": now,
    }
    if existing:
        await session.execute(
            update(PinListingsOrm)
            .where(PinListingsOrm.id == existing.id)
            .values(
                price_minor=price_minor,
                currency="USD",
                status="listed",
                license_type="personal_use",
                updated_at=now,
                **attest,
            )
        )
    else:
        session.add(
            PinListingsOrm(
                pin_id=pin.id,
                seller_user_id=seller.id,
                license_type="personal_use",
                price_minor=price_minor,
                currency="USD",
                status="listed",
                **attest,
            )
        )
    await session.flush()
    # Watermarked preview while listed
    generate_pin_preview.run(pin.id, watermarked=True)


async def create_pin_from_bytes(
    session,
    *,
    author: UsersOrm,
    category: str,
    photo: dict,
    tag: TagsOrm,
    list_for_sale: bool,
) -> bool:
    pexels_id = int(photo["id"])
    title = pin_title(category, pexels_id)
    dup = await session.scalar(select(PinsOrm.id).where(PinsOrm.title == title))
    if dup is not None:
        print(f"  skip exists {title}")
        return False

    src = (
        (photo.get("src") or {}).get("large2x")
        or (photo.get("src") or {}).get("large")
        or (photo.get("src") or {}).get("original")
    )
    if not src:
        print(f"  skip no src pexels#{pexels_id}")
        return False

    try:
        raw = _http_bytes(src)
    except Exception as e:
        print(f"  download fail pexels#{pexels_id}: {e}")
        return False

    ext = ".jpg"
    lower = src.lower().split("?")[0]
    if lower.endswith(".png"):
        ext = ".png"
    elif lower.endswith(".webp"):
        ext = ".webp"

    filename = f"{uuid.uuid4()}{ext}"
    dest = original_dir() / filename
    dest.write_bytes(raw)
    original_rel = f"pins/original/{filename}"

    photographer = (photo.get("photographer") or "Pexels").strip()[:80]
    pin = PinsOrm(
        user_id=author.id,
        title=title[:200],
        description=f"{category} · photo by {photographer} (Pexels)"[:400],
        original_image=original_rel,
    )
    session.add(pin)
    await session.flush()
    session.add(PinStatsOrm(pin_id=pin.id, view_count=0))
    await session.execute(
        pg_insert(pins_tags)
        .values(pin_id=pin.id, tag_id=tag.id)
        .on_conflict_do_nothing(index_elements=["pin_id", "tag_id"])
    )
    await session.commit()

    pin_id = pin.id
    # Clean preview first (sync Celery task body)
    generate_pin_preview.run(pin_id, watermarked=False)
    session.expire_all()
    pin = await session.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))

    if list_for_sale:
        await ensure_seller_listable(session, author)
        pin = await session.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
        if not pin or not pin.image or not pin.content_sha256:
            print(f"  WARN media incomplete for pin {pin_id}, skip list")
            await session.commit()
            return True
        await list_pin(session, pin, author)
        await session.commit()
        print(f"  listed pin {pin_id} @{author.username}")
    else:
        print(f"  created pin {pin_id} @{author.username} tag={tag.name}")
    return True


async def run(*, force: bool) -> None:
    api_key = _api_key()

    async with async_session_maker() as session:
        existing_count = int(
            await session.scalar(
                select(func.count()).select_from(PinsOrm).where(PinsOrm.title.like(f"{MARKER}%"))
            )
            or 0
        )
        target = CATEGORIES * PER_CATEGORY
        if existing_count >= target and not force:
            print(
                f"Already have {existing_count} {MARKER} pins (>= {target}). "
                "Pass --force to add missing ids / re-roll categories."
            )
            return

        sellers, others = await load_authors(session)
        if not sellers and not others:
            print("ERROR: no eligible authors (non-admin, non-org)", file=sys.stderr)
            sys.exit(1)
        if not sellers:
            print("WARN: no sellers — all pins will be non-listed")
        if not others:
            print("WARN: no non-seller authors — seller share may exceed 25%")

        categories = random.sample(CATEGORY_POOL, k=min(CATEGORIES, len(CATEGORY_POOL)))
        print(f"categories: {categories}")
        print(
            f"authors: sellers={[u.username for u in sellers]} "
            f"others={len(others)} users"
        )

        # Pre-bump sellers once so listing works
        for s in sellers:
            await ensure_seller_listable(session, s)
        await session.commit()

        seller_budget = int(round(target * SELLER_SHARE)) if sellers else 0
        seller_used = 0
        created = 0
        listed = 0

        for cat in categories:
            print(f"\n== {cat} ==")
            tag = await ensure_tag(session, cat)
            await session.commit()

            try:
                photos = pexels_search(cat, per_page=PER_CATEGORY, api_key=api_key)
            except Exception:
                continue
            if not photos:
                print(f"  no photos for {cat}")
                continue

            for photo in photos[:PER_CATEGORY]:
                use_seller = bool(sellers) and seller_used < seller_budget
                if use_seller:
                    author = random.choice(sellers)
                    for_sale = True
                elif others:
                    author = random.choice(others)
                    for_sale = False
                elif sellers:
                    author = random.choice(sellers)
                    for_sale = True
                else:
                    break

                ok = await create_pin_from_bytes(
                    session,
                    author=author,
                    category=cat,
                    photo=photo,
                    tag=tag,
                    list_for_sale=for_sale,
                )
                if ok:
                    created += 1
                    if for_sale:
                        seller_used += 1
                        listed += 1

        print(f"\nDONE created={created} listed={listed} seller_budget={seller_budget}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Pexels feed pins")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Do not early-exit when >=100 [pexels-seed] pins already exist",
    )
    args = parser.parse_args()
    asyncio.run(run(force=args.force))


if __name__ == "__main__":
    main()
