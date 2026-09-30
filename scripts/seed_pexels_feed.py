"""Seed feed pins by category/tag (soft-live demo).

Default image source: Picsum (no API key; reliable on VPS).
Optional: IMAGE_PROVIDER=loremflickr|pexels (often 401/403 from datacenters).
Tags still come from our category list (Picsum images are seeded per category name).

Rules (CHỐT):
- 10 random categories × 10 images = 100 pins
- Reuse existing tags (case-insensitive); create if missing
- Authors: all non-admin, non-organization users
- ~25 pins assigned to sellers → always listed ($1–$10 USD)
- ~75 pins assigned to non-seller authors → not listed
- Idempotent: skip if title `[feed-seed] … #{id}` already exists
- `--force` skips the “batch already complete” early exit

Usage:
  docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec -T \
    -w /fastapi -e PYTHONPATH=/fastapi fastapi-app \
    python -m scripts.seed_pexels_feed
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
from urllib.parse import quote, quote_plus
from urllib.request import Request, urlopen

from sqlalchemy import func, or_, select, update
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

MARKER = "[feed-seed]"
LEGACY_MARKER = "[pexels-seed]"
CATEGORIES = 10
PER_CATEGORY = 10
SELLER_SHARE = 0.25
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


def _provider() -> str:
    # picsum: no key, works on most VPS; loremflickr/pexels often 401/403 from datacenters
    return (os.getenv("IMAGE_PROVIDER") or "picsum").strip().lower()


def _http_json(url: str, *, headers: dict[str, str] | None = None) -> dict:
    hdrs = {
        "User-Agent": "Mozilla/5.0 (compatible; art-marketplace-seed/1.0)",
        "Accept": "application/json",
    }
    if headers:
        hdrs.update(headers)
    req = Request(url, headers=hdrs)
    try:
        with urlopen(req, timeout=60) as resp:
            import json

            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        raise HTTPError(e.url, e.code, f"{e.reason} body={body!r}", e.headers, None) from e


def _http_bytes(url: str) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; art-marketplace-seed/1.0)",
            "Accept": "image/*,*/*",
        },
    )
    with urlopen(req, timeout=120) as resp:
        data = resp.read()
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "html" in ctype or data[:15].lstrip().lower().startswith(b"<!doctype"):
            raise ValueError(f"got HTML instead of image from {url}")
        if len(data) < 1000:
            raise ValueError(f"image too small ({len(data)} bytes) from {url}")
        return data


def _flickr_tag_path(category: str) -> str:
    # loremflickr: /width/height/tag1,tag2
    parts = [p for p in category.replace("-", " ").split() if p]
    return quote(",".join(parts), safe=",")


def photos_loremflickr(category: str, *, per_page: int) -> list[dict]:
    """Build deterministic Flickr-tag URLs (no search API)."""
    tag_path = _flickr_tag_path(category)
    out: list[dict] = []
    for i in range(1, per_page + 1):
        lock = abs(hash(f"{category}:{i}")) % 10_000_000
        # lock keeps image stable across runs for same category+index
        url = f"https://loremflickr.com/800/1200/{tag_path}/all?lock={lock}"
        out.append(
            {
                "id": f"flickr-{category.replace(' ', '-')}-{i}",
                "src": {"original": url},
                "photographer": "Lorem Flickr",
                "source": "loremflickr",
            }
        )
    return out


def photos_picsum(category: str, *, per_page: int) -> list[dict]:
    out: list[dict] = []
    for i in range(1, per_page + 1):
        seed = quote_plus(f"{category}-{i}")
        url = f"https://picsum.photos/seed/{seed}/800/1200"
        out.append(
            {
                "id": f"picsum-{category.replace(' ', '-')}-{i}",
                "src": {"original": url},
                "photographer": "Picsum",
                "source": "picsum",
            }
        )
    return out


def photos_pexels(query: str, *, per_page: int, api_key: str) -> list[dict]:
    url = (
        "https://api.pexels.com/v1/search"
        f"?query={quote_plus(query)}&per_page={per_page}&orientation=portrait"
    )
    data = _http_json(url, headers={"Authorization": api_key})
    photos = []
    for p in data.get("photos") or []:
        photos.append(
            {
                "id": str(p["id"]),
                "src": p.get("src") or {},
                "photographer": p.get("photographer") or "Pexels",
                "source": "pexels",
            }
        )
    return photos


def fetch_photos(category: str, *, per_page: int) -> list[dict]:
    provider = _provider()
    if provider == "pexels":
        key = (os.getenv("PEXELS_API_KEY") or "").strip()
        if not key:
            print("ERROR: IMAGE_PROVIDER=pexels requires PEXELS_API_KEY", file=sys.stderr)
            sys.exit(1)
        try:
            return photos_pexels(category, per_page=per_page, api_key=key)
        except Exception as e:
            print(f"Pexels failed for {category!r}: {e} — falling back to loremflickr", file=sys.stderr)
            return photos_loremflickr(category, per_page=per_page)
    if provider == "picsum":
        return photos_picsum(category, per_page=per_page)
    return photos_loremflickr(category, per_page=per_page)


def pin_title(category: str, photo_id: str) -> str:
    return f"{MARKER} {category} #{photo_id}"


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


async def ensure_seller_listable(session, user_id: int, username: str) -> None:
    min_n = settings.MP_ELIGIBILITY_MIN_PINS
    min_m = settings.MP_ELIGIBILITY_MIN_VIEWS

    pin_ids = list(
        (await session.scalars(select(PinsOrm.id).where(PinsOrm.user_id == user_id))).all()
    )
    while len(pin_ids) < min_n:
        stub = PinsOrm(
            user_id=user_id,
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
            .where(PinsOrm.user_id == user_id)
        )
        or 0
    )
    if total_views >= min_m:
        return

    need = min_m - total_views
    first_id = pin_ids[0]
    stats = await session.get(PinStatsOrm, first_id)
    if stats is None:
        session.add(PinStatsOrm(pin_id=first_id, view_count=need))
    else:
        stats.view_count = int(stats.view_count or 0) + need
    print(f"  bumped views for {username}: +{need} (target M>={min_m})")


async def list_pin(session, pin: PinsOrm, seller_user_id: int) -> None:
    price_minor = random.randint(100, 1000)
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
                seller_user_id=seller_user_id,
                license_type="personal_use",
                price_minor=price_minor,
                currency="USD",
                status="listed",
                **attest,
            )
        )
    await session.flush()
    generate_pin_preview.run(pin.id, watermarked=True)


def _download_with_fallback(category: str, photo: dict, index: int) -> tuple[bytes, str] | None:
    src = (
        (photo.get("src") or {}).get("large2x")
        or (photo.get("src") or {}).get("large")
        or (photo.get("src") or {}).get("original")
    )
    urls: list[str] = []
    seed = quote_plus(f"{category}-fb-{index}-{photo.get('id')}")
    picsum = f"https://picsum.photos/seed/{seed}/800/1200"
    # Prefer picsum first — flickr/pexels often blocked on VPS
    if photo.get("source") == "picsum" and src:
        urls.append(src)
    else:
        urls.append(picsum)
        if src and src != picsum:
            urls.append(src)

    last_err: Exception | None = None
    for url in urls:
        try:
            return _http_bytes(url), url
        except Exception as e:
            last_err = e
            print(f"  download fail {url}: {e}")
    print(f"  give up photo {photo.get('id')}: {last_err}")
    return None


async def create_pin_from_bytes(
    session,
    *,
    author: UsersOrm,
    category: str,
    photo: dict,
    tag: TagsOrm,
    list_for_sale: bool,
    index: int,
) -> bool:
    photo_id = str(photo["id"])
    title = pin_title(category, photo_id)
    author_id = author.id
    author_username = author.username

    dup = await session.scalar(select(PinsOrm.id).where(PinsOrm.title == title))
    if dup is not None:
        print(f"  skip exists {title}")
        return False

    got = _download_with_fallback(category, photo, index)
    if got is None:
        return False
    raw, final_url = got

    ext = ".jpg"
    lower = final_url.lower().split("?")[0]
    if lower.endswith(".png"):
        ext = ".png"
    elif lower.endswith(".webp"):
        ext = ".webp"

    filename = f"{uuid.uuid4()}{ext}"
    dest = original_dir() / filename
    dest.write_bytes(raw)
    original_rel = f"pins/original/{filename}"

    photographer = (photo.get("photographer") or photo.get("source") or "seed").strip()[:80]
    source = photo.get("source") or "seed"
    pin = PinsOrm(
        user_id=author_id,
        title=title[:200],
        description=f"{category} · {photographer} ({source})"[:400],
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
    generate_pin_preview.run(pin_id, watermarked=False)
    session.expire_all()

    if list_for_sale:
        await ensure_seller_listable(session, author_id, author_username)
        pin = await session.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
        if not pin or not pin.image or not pin.content_sha256:
            print(f"  WARN media incomplete for pin {pin_id}, skip list")
            await session.commit()
            return True
        await list_pin(session, pin, author_id)
        await session.commit()
        print(f"  listed pin {pin_id} @{author_username}")
    else:
        print(f"  created pin {pin_id} @{author_username} tag={tag.name}")
    return True


async def run(*, force: bool) -> None:
    async with async_session_maker() as session:
        existing_count = int(
            await session.scalar(
                select(func.count())
                .select_from(PinsOrm)
                .where(
                    or_(
                        PinsOrm.title.like(f"{MARKER}%"),
                        PinsOrm.title.like(f"{LEGACY_MARKER}%"),
                    )
                )
            )
            or 0
        )
        target = CATEGORIES * PER_CATEGORY
        if existing_count >= target and not force:
            print(
                f"Already have {existing_count} seed pins (>= {target}). "
                "Pass --force to continue."
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
        print(f"provider={_provider()}")
        print(f"categories: {categories}")
        print(
            f"authors: sellers={[u.username for u in sellers]} "
            f"others={len(others)} users"
        )

        for s in sellers:
            await ensure_seller_listable(session, s.id, s.username)
        await session.commit()

        seller_budget = int(round(target * SELLER_SHARE)) if sellers else 0
        seller_used = 0
        created = 0
        listed = 0

        for cat in categories:
            print(f"\n== {cat} ==")
            try:
                photos = fetch_photos(cat, per_page=PER_CATEGORY)
            except Exception as e:
                print(f"  fetch failed: {e}")
                continue
            if not photos:
                print(f"  no photos for {cat}")
                continue

            tag = await ensure_tag(session, cat)
            await session.commit()

            for idx, photo in enumerate(photos[:PER_CATEGORY], start=1):
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
                    index=idx,
                )
                if ok:
                    created += 1
                    if for_sale:
                        seller_used += 1
                        listed += 1

        print(f"\nDONE created={created} listed={listed} seller_budget={seller_budget}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed feed pins by category")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Do not early-exit when >=100 seed pins already exist",
    )
    args = parser.parse_args()
    asyncio.run(run(force=args.force))


if __name__ == "__main__":
    main()
