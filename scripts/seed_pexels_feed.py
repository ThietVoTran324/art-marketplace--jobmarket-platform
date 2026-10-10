"""Seed feed pins from DB tags (soft-live demo).

Default image source: Met Museum API v1.1 (no key). Fallback: Picsum.
Optional: IMAGE_PROVIDER=picsum|loremflickr|pexels|met.

Rules:
- Load tags already in DB; fill each until pin-count >= --per-tag
- Met search query mapped per tag (not random); franchise/niche → Picsum
- Multi-tag: primary + related bundle members that exist in DB
  + Met subject terms fuzzy-matched to existing tags (cap 5)
- Authors: non-admin, non-org; ~25% listed on sellers
- Idempotent: title `[feed-seed] {tag} #{photo_id}`

Usage:
  ... python -m scripts.seed_pexels_feed --per-tag 20
  ... python -m scripts.seed_pexels_feed --per-tag 15 --force
"""
from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import quote, quote_plus
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

MARKER = "[feed-seed]"
DEFAULT_PER_TAG = 20
SELLER_SHARE = 0.25
MAX_TAGS_PER_PIN = 5

MET_SEARCH = "https://collectionapi.metmuseum.org/public/collection/v1.1/search"
MET_OBJECT = "https://collectionapi.metmuseum.org/public/collection/v1/objects"


@dataclass(frozen=True)
class Author:
    id: int
    username: str


@dataclass(frozen=True)
class DbTag:
    id: int
    name: str
    pin_count: int


# Met keyword per DB tag (lowercase keys). Missing → search raw tag name.
MET_QUERIES: dict[str, str] = {
    "abstract art": "abstract art",
    "artistic ceramics": "ceramic pottery",
    "art prints": "print engraving",
    "böcklin": "bocklin",
    "brand": "advertisement poster",
    "branding": "advertisement poster",
    "calligraphy": "calligraphy manuscript",
    "canvas": "oil painting canvas",
    "caspar david friedrich": "caspar david friedrich",
    "ceramic art": "ceramic pottery",
    "character design": "portrait figure drawing",
    "classic": "classical painting",
    "collage art": "collage",
    "color": "color study painting",
    "decord art": "decorative art",
    "design": "design poster",
    "digital art": "contemporary art",
    "fashion": "fashion costume",
    "fashion photography": "fashion photograph",
    "figure": "figure drawing nude study",
    "fine art": "painting",
    "floral art": "flowers still life",
    "flowwer": "flowers",
    "graffiti": "graffiti street art",
    "grap": "graphic design poster",
    "graphic design": "poster graphic",
    "illustration": "drawing illustration",
    "impressionism": "impressionist painting",
    "journaling": "sketchbook drawing",
    "landscape photography": "landscape photograph",
    "logo": "emblem seal crest",
    "merchandise design": "poster advertisement",
    "minimalism": "minimal abstract",
    "motion graphic": "poster design",
    "natural": "nature landscape",
    "nature photography": "nature photograph",
    "oil": "oil painting",
    "oil painting": "oil painting",
    "oil style": "oil painting",
    "painting": "painting",
    "pakeage desing": "package design poster",
    "physic art": "anatomy figure drawing",
    "plei air": "plein air landscape",
    "portrait photography": "portrait photograph",
    "poster design": "poster",
    "pottery": "pottery ceramic",
    "realism": "realist painting",
    "romanticism": "romantic landscape painting",
    "sketchbook": "sketchbook drawing",
    "stationery merch": "print design",
    "surreal art": "surrealism",
    "tonalism": "tonalist landscape",
    "typography": "calligraphy typography",
    "uiux": "poster design",
    "van gogh": "van gogh",
    "vintage photography": "vintage photograph",
    "watercolor": "watercolor painting",
    "anime": "japanese print ukiyo-e",
    "armor": "armor",
    "book": "illuminated manuscript",
    "cover": "book cover print",
    "cyberpunk": "futuristic city",
    "fanart": "portrait drawing",
    "game": "battle scene painting",
    "game world envirment": "landscape architecture",
    "knight": "knight armor",
    "studio": "artist studio",
    "template": "ornament pattern",
    "toy": "toy figurine",
    "tool": "tools still life",
    "eye": "eye drawing",
    "house": "house architecture",
    "human": "portrait figure",
    "moblie": "telephone design",
    "ppt": "diagram print",
    "live": "performance painting",
}

# Tags Met cannot match well — use Picsum (still attaches real DB tags).
PICSUM_ONLY: set[str] = {
    "ai",
    "doggo",
    "eldenring",
    "ff2",
    "gojo",
    "lol",
    "radagon",
    "rd2",
    "soulgame",
    "swain",
}

# Related tag bundles (lowercase). Pin gets primary + other members present in DB.
RELATED_BUNDLES: list[set[str]] = [
    {
        "painting",
        "oil painting",
        "oil",
        "oil style",
        "fine art",
        "canvas",
        "plein air",
        "plei air",
        "impressionism",
        "realism",
        "romanticism",
        "tonalism",
        "watercolor",
        "abstract art",
        "surreal art",
        "floral art",
        "flowwer",
        "figure",
        "classic",
        "van gogh",
        "böcklin",
        "caspar david friedrich",
    },
    {
        "graphic design",
        "design",
        "poster design",
        "logo",
        "brand",
        "branding",
        "typography",
        "calligraphy",
        "uiux",
        "minimalism",
        "collage art",
        "merchandise design",
        "stationery merch",
        "motion graphic",
        "pakeage desing",
        "grap",
        "template",
        "ppt",
        "decord art",
    },
    {
        "illustration",
        "digital art",
        "character design",
        "sketchbook",
        "journaling",
        "anime",
        "fanart",
        "graffiti",
        "cyberpunk",
    },
    {
        "artistic ceramics",
        "ceramic art",
        "pottery",
        "art prints",
    },
    {
        "portrait photography",
        "landscape photography",
        "fashion photography",
        "vintage photography",
        "nature photography",
        "fashion",
        "natural",
    },
    {
        "game",
        "game world envirment",
        "soulgame",
        "eldenring",
        "armor",
        "knight",
        "fanart",
    },
]


def _provider() -> str:
    return (os.getenv("IMAGE_PROVIDER") or "met").strip().lower()


def _norm(name: str) -> str:
    return name.strip().lower()


def met_query_for(tag_name: str) -> str:
    return MET_QUERIES.get(_norm(tag_name), tag_name.strip())


def related_names_for(tag_name: str) -> set[str]:
    key = _norm(tag_name)
    out: set[str] = set()
    for bundle in RELATED_BUNDLES:
        if key in bundle:
            out |= bundle
    out.discard(key)
    return out


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
    parts = [p for p in category.replace("-", " ").split() if p]
    return quote(",".join(parts), safe=",")


def photos_loremflickr(category: str, *, per_page: int) -> list[dict]:
    tag_path = _flickr_tag_path(category)
    out: list[dict] = []
    for i in range(1, per_page + 1):
        lock = abs(hash(f"{category}:{i}")) % 10_000_000
        url = f"https://loremflickr.com/800/1200/{tag_path}/all?lock={lock}"
        out.append(
            {
                "id": f"flickr-{category.replace(' ', '-')}-{i}",
                "src": {"original": url},
                "photographer": "Lorem Flickr",
                "source": "loremflickr",
                "met_tags": [],
            }
        )
    return out


def photos_picsum(category: str, *, per_page: int) -> list[dict]:
    out: list[dict] = []
    for i in range(1, per_page + 1):
        seed = quote_plus(f"{category}-{i}-{random.randint(1, 10_000)}")
        url = f"https://picsum.photos/seed/{seed}/800/1200"
        out.append(
            {
                "id": f"picsum-{category.replace(' ', '-')}-{i}-{seed}",
                "src": {"original": url},
                "photographer": "Picsum",
                "source": "picsum",
                "met_tags": [],
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
                "met_tags": [],
            }
        )
    return photos


def photos_met(category: str, *, per_page: int) -> list[dict]:
    q = met_query_for(category)
    limit = min(max(per_page * 4, 40), 100)
    search_url = (
        f"{MET_SEARCH}?q={quote_plus(q)}"
        f"&hasImages=true&isPublicDomain=true&limit={limit}"
    )
    data = _http_json(search_url)
    ids = list(data.get("objectIDs") or data.get("objectIds") or [])
    if not ids:
        raise ValueError(f"Met search empty for q={q!r}")
    random.shuffle(ids)

    out: list[dict] = []
    scanned = 0
    for oid in ids:
        if len(out) >= per_page:
            break
        scanned += 1
        if scanned > max(per_page * 8, 40):
            break
        try:
            obj = _http_json(f"{MET_OBJECT}/{oid}")
        except Exception:
            continue
        finally:
            time.sleep(0.05)

        img = (obj.get("primaryImageSmall") or obj.get("primaryImage") or "").strip()
        if not img.startswith("http"):
            continue
        artist = (obj.get("artistDisplayName") or "Metropolitan Museum").strip()[:80]
        subject_tags = [
            str(t.get("term")).strip()
            for t in (obj.get("tags") or [])
            if isinstance(t, dict) and t.get("term")
        ]
        out.append(
            {
                "id": f"met-{oid}",
                "src": {"original": img, "large": img},
                "photographer": artist or "Met",
                "source": "met",
                "met_tags": subject_tags,
                "met_classification": (obj.get("classification") or "").strip(),
                "met_medium": (obj.get("medium") or "").strip(),
            }
        )
    if not out:
        raise ValueError(f"Met returned no downloadable images for q={q!r}")
    return out


def fetch_photos(category: str, *, per_page: int) -> list[dict]:
    if _norm(category) in PICSUM_ONLY:
        return photos_picsum(category, per_page=per_page)

    provider = _provider()
    if provider == "met":
        try:
            return photos_met(category, per_page=per_page)
        except Exception as e:
            print(
                f"Met failed for {category!r}: {e} — falling back to picsum",
                file=sys.stderr,
            )
            return photos_picsum(category, per_page=per_page)
    if provider == "pexels":
        key = (os.getenv("PEXELS_API_KEY") or "").strip()
        if not key:
            print("ERROR: IMAGE_PROVIDER=pexels requires PEXELS_API_KEY", file=sys.stderr)
            sys.exit(1)
        try:
            return photos_pexels(met_query_for(category), per_page=per_page, api_key=key)
        except Exception as e:
            print(
                f"Pexels failed for {category!r}: {e} — falling back to picsum",
                file=sys.stderr,
            )
            return photos_picsum(category, per_page=per_page)
    if provider == "picsum":
        return photos_picsum(category, per_page=per_page)
    if provider == "loremflickr":
        return photos_loremflickr(category, per_page=per_page)
    print(f"WARN unknown IMAGE_PROVIDER={provider!r}, using met", file=sys.stderr)
    return photos_met(category, per_page=per_page)


def pin_title(category: str, photo_id: str) -> str:
    return f"{MARKER} {category} #{photo_id}"


def pick_extra_tag_ids(
    *,
    primary: DbTag,
    photo: dict,
    by_lower: dict[str, DbTag],
) -> list[int]:
    """Primary + related DB tags + Met subjects that match existing tags."""
    chosen: list[int] = [primary.id]
    seen = {primary.id}

    related = list(related_names_for(primary.name))
    random.shuffle(related)
    for name in related:
        tag = by_lower.get(name)
        if tag and tag.id not in seen:
            chosen.append(tag.id)
            seen.add(tag.id)
        if len(chosen) >= MAX_TAGS_PER_PIN:
            return chosen

    # Fuzzy: Met subject "Landscapes" → db "landscape photography" etc.
    for term in photo.get("met_tags") or []:
        tnorm = _norm(term)
        # exact
        hit = by_lower.get(tnorm)
        if not hit:
            # substring either way
            for key, tag in by_lower.items():
                if tnorm in key or key in tnorm:
                    hit = tag
                    break
        if hit and hit.id not in seen:
            chosen.append(hit.id)
            seen.add(hit.id)
        if len(chosen) >= MAX_TAGS_PER_PIN:
            break

    # Medium hint: "Oil on canvas" → oil painting / canvas
    medium = _norm(str(photo.get("met_medium") or ""))
    if "oil" in medium:
        for key in ("oil painting", "oil", "oil style", "painting", "canvas"):
            tag = by_lower.get(key)
            if tag and tag.id not in seen:
                chosen.append(tag.id)
                seen.add(tag.id)
            if len(chosen) >= MAX_TAGS_PER_PIN:
                break
    if "watercolor" in medium or "watercolour" in medium:
        tag = by_lower.get("watercolor")
        if tag and tag.id not in seen and len(chosen) < MAX_TAGS_PER_PIN:
            chosen.append(tag.id)

    return chosen


async def load_db_tags(session) -> list[DbTag]:
    rows = await session.execute(
        select(
            TagsOrm.id,
            TagsOrm.name,
            func.count(pins_tags.c.pin_id),
        )
        .outerjoin(pins_tags, pins_tags.c.tag_id == TagsOrm.id)
        .group_by(TagsOrm.id)
        .order_by(func.count(pins_tags.c.pin_id).asc(), TagsOrm.name.asc())
    )
    return [
        DbTag(id=int(i), name=str(n), pin_count=int(c or 0)) for i, n, c in rows.all()
    ]


async def load_authors(session) -> tuple[list[Author], list[Author]]:
    users = list((await session.scalars(select(UsersOrm).order_by(UsersOrm.id))).all())
    sellers: list[Author] = []
    others: list[Author] = []
    for u in users:
        uid = int(u.id)
        uname = str(u.username)
        roles = await get_user_roles(session, uid)
        if "admin" in roles:
            continue
        if await is_organization_user(session, uid):
            continue
        author = Author(id=uid, username=uname)
        if "seller" in roles:
            sellers.append(author)
        else:
            others.append(author)
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
    seed = quote_plus(f"{category}-fb-{index}-{photo.get('id')}-{random.randint(1, 9999)}")
    picsum = f"https://picsum.photos/seed/{seed}/800/1200"
    urls: list[str] = []
    source = photo.get("source")
    if source in ("met", "pexels") and src:
        urls.extend([src, picsum])
    elif source == "picsum" and src:
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
    author: Author,
    category: str,
    photo: dict,
    tag_ids: list[int],
    tag_name: str,
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

    for tid in tag_ids:
        await session.execute(
            pg_insert(pins_tags)
            .values(pin_id=pin.id, tag_id=tid)
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
        print(f"  listed pin {pin_id} @{author_username} tags={len(tag_ids)}")
    else:
        print(
            f"  created pin {pin_id} @{author_username} primary={tag_name!r} "
            f"tags={len(tag_ids)}"
        )
    return True


async def run(*, force: bool, per_tag: int) -> None:
    per_tag = max(1, min(per_tag, 50))

    async with async_session_maker() as session:
        tags = await load_db_tags(session)
        if not tags:
            print("ERROR: no tags in DB", file=sys.stderr)
            sys.exit(1)

        by_lower = {_norm(t.name): t for t in tags}
        # Prefer first-seen casing when duplicates differ only by case —
        # both rows still get filled when we iterate all tags.

        sellers, others = await load_authors(session)
        if not sellers and not others:
            print("ERROR: no eligible authors (non-admin, non-org)", file=sys.stderr)
            sys.exit(1)

        need_tags = [
            t
            for t in tags
            if force or t.pin_count < per_tag
        ]
        # Estimate new pins (multi-tag means real inserts < sum of needs)
        est = sum(
            (per_tag if force else max(0, per_tag - t.pin_count)) for t in need_tags
        )

        print(f"provider={_provider()}")
        print(f"db_tags={len(tags)} to_fill={len(need_tags)} per_tag={per_tag} est≈{est}")
        print(
            f"authors: sellers={[u.username for u in sellers]} "
            f"others={len(others)} users"
        )

        for s in sellers:
            await ensure_seller_listable(session, s.id, s.username)
        await session.commit()

        seller_budget = int(round(est * SELLER_SHARE)) if sellers else 0
        seller_used = 0
        created = 0
        listed = 0

        for tag in need_tags:
            # Refresh count (earlier multi-tag pins may have filled this tag)
            live = int(
                await session.scalar(
                    select(func.count())
                    .select_from(pins_tags)
                    .where(pins_tags.c.tag_id == tag.id)
                )
                or 0
            )
            need = per_tag if force else max(0, per_tag - live)
            src = "picsum" if _norm(tag.name) in PICSUM_ONLY else _provider()
            print(f"\n== {tag.name} (id={tag.id}) count={live} need={need} src={src} ==")
            if need <= 0:
                print("  skip (already at target)")
                continue

            try:
                photos = fetch_photos(tag.name, per_page=min(need + 5, 50))
            except Exception as e:
                print(f"  fetch failed: {e}")
                continue
            if not photos:
                print("  no photos")
                continue

            filled = 0
            for idx, photo in enumerate(photos, start=1):
                if filled >= need:
                    break
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

                tag_ids = pick_extra_tag_ids(
                    primary=tag, photo=photo, by_lower=by_lower
                )
                try:
                    ok = await create_pin_from_bytes(
                        session,
                        author=author,
                        category=tag.name,
                        photo=photo,
                        tag_ids=tag_ids,
                        tag_name=tag.name,
                        list_for_sale=for_sale,
                        index=idx,
                    )
                except Exception as e:
                    print(f"  ERROR pin {photo.get('id')}: {e}", file=sys.stderr)
                    try:
                        await session.rollback()
                    except Exception:
                        pass
                    continue
                if ok:
                    filled += 1
                    created += 1
                    if for_sale:
                        seller_used += 1
                        listed += 1

        print(f"\nDONE created={created} listed={listed} seller_budget={seller_budget}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed feed pins from DB tags")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Add another per-tag batch even if tag already at target",
    )
    parser.add_argument(
        "--per-tag",
        type=int,
        default=DEFAULT_PER_TAG,
        help=f"Target pins per DB tag (default {DEFAULT_PER_TAG}, max 50)",
    )
    args = parser.parse_args()
    asyncio.run(run(force=args.force, per_tag=args.per_tag))


if __name__ == "__main__":
    main()
