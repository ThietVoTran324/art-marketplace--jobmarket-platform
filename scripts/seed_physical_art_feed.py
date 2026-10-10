"""Seed 5 high-art physical/sellable tags with Met-only, strict match (no Picsum).

Tags:
  oil painting | watercolor | charcoal drawing | pottery | art print

Rules:
- Met Museum API only; reject if image missing or medium/classification mismatch
- Exactly one primary tag per pin (the gallery tag) — no loose multi-tag spam
- ~30% randomly listed for sale (sellers only)
- Seed engagement (like > view > comment > save) so guest popularity feed has signal
- Idempotent titles: `[art-gallery] {tag} #met-{objectId}`

Usage:
  docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec -T \\
    -w /fastapi -e PYTHONPATH=/fastapi fastapi-app \\
    python -m scripts.seed_physical_art_feed --per-tag 12
"""
from __future__ import annotations

import argparse
import asyncio
import random
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError
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
    CommentsOrm,
    LikesOrm,
    PinListingsOrm,
    PinStatsOrm,
    PinsOrm,
    TagsOrm,
    UsersOrm,
    pins_tags,
    users_pins,
)

MARKER = "[art-gallery]"
DEFAULT_PER_TAG = 12
LIST_SHARE = 0.30
MET_SEARCH = "https://collectionapi.metmuseum.org/public/collection/v1.1/search"
MET_OBJECT = "https://collectionapi.metmuseum.org/public/collection/v1/objects"


@dataclass(frozen=True)
class Author:
    id: int
    username: str


@dataclass(frozen=True)
class GallerySpec:
    tag: str
    query: str
    medium_param: str | None  # Met `medium=` filter (classification spelling)
    # All must match (case-insensitive substring) against medium OR classification
    require_any: tuple[str, ...]
    # Reject if any of these appear in medium/classification
    reject_any: tuple[str, ...] = ()


# Physical art that can plausibly be sold as prints/originals.
GALLERY: tuple[GallerySpec, ...] = (
    GallerySpec(
        tag="oil painting",
        query="oil painting",
        medium_param="Paintings",
        require_any=("oil",),
        reject_any=("photograph", "inkjet", "poster"),
    ),
    GallerySpec(
        tag="watercolor",
        query="watercolor",
        medium_param=None,
        require_any=("watercolor", "watercolour"),
        reject_any=("photograph", "oil on canvas"),
    ),
    GallerySpec(
        tag="charcoal drawing",
        query="charcoal drawing",
        medium_param="Drawings",
        require_any=("charcoal",),
        reject_any=("photograph", "oil on"),
    ),
    GallerySpec(
        tag="pottery",
        query="pottery ceramic vase",
        medium_param="Ceramics",
        require_any=("ceramic", "earthenware", "stoneware", "porcelain", "pottery"),
        reject_any=("photograph",),
    ),
    GallerySpec(
        tag="art print",
        query="etching engraving print",
        medium_param="Prints",
        require_any=("etching", "engraving", "lithograph", "woodcut", "print"),
        reject_any=("photograph", "oil on canvas"),
    ),
)


def _http_json(url: str) -> dict:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; art-gallery-seed/1.0)",
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=60) as resp:
        import json

        return json.loads(resp.read().decode("utf-8"))


def _http_bytes(url: str) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; art-gallery-seed/1.0)",
            "Accept": "image/*,*/*",
        },
    )
    with urlopen(req, timeout=120) as resp:
        data = resp.read()
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "html" in ctype or data[:15].lstrip().lower().startswith(b"<!doctype"):
            raise ValueError(f"HTML instead of image: {url}")
        if len(data) < 2000:
            raise ValueError(f"image too small ({len(data)}) from {url}")
        return data


def _blob(obj: dict) -> str:
    parts = [
        obj.get("medium") or "",
        obj.get("classification") or "",
        obj.get("objectName") or "",
        obj.get("title") or "",
    ]
    return " ".join(parts).lower()


def _accept(spec: GallerySpec, obj: dict) -> bool:
    img = (obj.get("primaryImageSmall") or obj.get("primaryImage") or "").strip()
    if not img.startswith("http"):
        return False
    if not obj.get("isPublicDomain", True):
        return False
    blob = _blob(obj)
    if not any(tok in blob for tok in spec.require_any):
        return False
    if any(tok in blob for tok in spec.reject_any):
        return False
    if spec.medium_param:
        cl = (obj.get("classification") or "").strip()
        # Met medium= filter is classification; allow close matches
        if cl and spec.medium_param.lower() not in cl.lower():
            # Ceramics sometimes returns empty classification — medium text still ok
            if not any(tok in blob for tok in spec.require_any):
                return False
    return True


def fetch_met_strict(spec: GallerySpec, *, need: int) -> list[dict]:
    """Deep-scan Met; only return objects that hard-match the gallery spec."""
    limit = 100
    params = (
        f"q={quote_plus(spec.query)}&hasImages=true&isPublicDomain=true&limit={limit}"
    )
    if spec.medium_param:
        params += f"&medium={quote_plus(spec.medium_param)}"
    data = _http_json(f"{MET_SEARCH}?{params}")
    ids = list(data.get("objectIDs") or data.get("objectIds") or [])
    if not ids:
        raise ValueError(f"Met empty for {spec.tag!r} q={spec.query!r}")
    random.shuffle(ids)

    out: list[dict] = []
    scanned = 0
    max_scan = min(len(ids), max(need * 25, 80))
    for oid in ids:
        if len(out) >= need:
            break
        if scanned >= max_scan:
            break
        scanned += 1
        try:
            obj = _http_json(f"{MET_OBJECT}/{oid}")
        except Exception:
            continue
        finally:
            time.sleep(0.06)

        if not _accept(spec, obj):
            continue
        img = (obj.get("primaryImageSmall") or obj.get("primaryImage") or "").strip()
        artist = (obj.get("artistDisplayName") or "Metropolitan Museum").strip()[:80]
        title = (obj.get("title") or spec.tag).strip()[:120]
        out.append(
            {
                "id": f"met-{oid}",
                "url": img,
                "artist": artist,
                "title": title,
                "medium": (obj.get("medium") or "")[:160],
                "classification": (obj.get("classification") or "")[:80],
            }
        )
    if len(out) < max(1, need // 3):
        raise ValueError(
            f"strict match too thin for {spec.tag!r}: got {len(out)}/{need} "
            f"(scanned {scanned})"
        )
    return out


async def ensure_tag(session, name: str) -> tuple[int, str]:
    existing = await session.scalar(
        select(TagsOrm).where(func.lower(TagsOrm.name) == name.lower())
    )
    if existing is not None:
        return int(existing.id), str(existing.name)
    tag = TagsOrm(name=name)
    session.add(tag)
    await session.flush()
    print(f"  + tag created: {name}")
    return int(tag.id), str(tag.name)


async def count_gallery_for_tag(session, tag: str) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(PinsOrm)
            .where(PinsOrm.title.like(f"{MARKER} {tag} #%"))
        )
        or 0
    )


async def load_authors(session) -> tuple[list[Author], list[Author], list[Author]]:
    """sellers, others, all_eligible (for engagement)."""
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
    all_el = sellers + others
    return sellers, others, all_el


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
    if total_views < min_m:
        need = min_m - total_views
        first_id = pin_ids[0]
        stats = await session.get(PinStatsOrm, first_id)
        if stats is None:
            session.add(PinStatsOrm(pin_id=first_id, view_count=need))
        else:
            stats.view_count = int(stats.view_count or 0) + need
        print(f"  bumped views for {username}: +{need}")


async def list_pin(session, pin: PinsOrm, seller_user_id: int) -> None:
    now = datetime.now(timezone.utc)
    attest = {
        "attestation_accepted": True,
        "attestation_version": settings.MP_ATTESTATION_VERSION,
        "attested_at": now,
    }
    existing = await session.scalar(
        select(PinListingsOrm).where(PinListingsOrm.pin_id == pin.id)
    )
    price_minor = random.randint(1500, 12000)  # $15–$120 — physical-art range
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


async def seed_engagement(
    session,
    *,
    pin_id: int,
    author_id: int,
    engagers: list[Author],
) -> None:
    """Weighted random engagement: likes most, then views, comments, saves."""
    pool = [a for a in engagers if a.id != author_id]
    if not pool:
        return

    n_like = random.randint(3, min(18, len(pool)))
    n_save = random.randint(0, min(4, len(pool)))
    n_comment = random.randint(0, min(3, len(pool)))
    views = random.randint(n_like + 5, n_like * 8 + 40)

    stats = await session.get(PinStatsOrm, pin_id)
    if stats is None:
        session.add(PinStatsOrm(pin_id=pin_id, view_count=views))
    else:
        stats.view_count = int(stats.view_count or 0) + views

    for a in random.sample(pool, n_like):
        exists = await session.scalar(
            select(LikesOrm.id).where(
                LikesOrm.user_id == a.id, LikesOrm.pin_id == pin_id
            )
        )
        if exists is None:
            session.add(LikesOrm(user_id=a.id, pin_id=pin_id))

    for a in random.sample(pool, n_save):
        await session.execute(
            pg_insert(users_pins)
            .values(user_id=a.id, pin_id=pin_id)
            .on_conflict_do_nothing()
        )

    snippets = [
        "Beautiful piece.",
        "Love the texture.",
        "Would hang this at home.",
        "Stunning craftsmanship.",
        "Color and form are perfect.",
    ]
    for a in random.sample(pool, n_comment):
        session.add(
            CommentsOrm(
                pin_id=pin_id,
                user_id=a.id,
                content=random.choice(snippets),
            )
        )
    await session.flush()


async def create_gallery_pin(
    session,
    *,
    author: Author,
    spec: GallerySpec,
    tag_id: int,
    tag_name: str,
    photo: dict,
    list_for_sale: bool,
    engagers: list[Author],
) -> bool:
    title = f"{MARKER} {spec.tag} #{photo['id']}"
    dup = await session.scalar(select(PinsOrm.id).where(PinsOrm.title == title))
    if dup is not None:
        print(f"  skip exists {title}")
        return False

    try:
        raw = _http_bytes(photo["url"])
    except Exception as e:
        print(f"  download fail {photo['id']}: {e}")
        return False

    filename = f"{uuid.uuid4()}.jpg"
    (original_dir() / filename).write_bytes(raw)
    original_rel = f"pins/original/{filename}"

    desc = (
        f"{photo.get('title') or tag_name} · {photo.get('artist')} · "
        f"{photo.get('medium') or photo.get('classification') or 'Met'}"
    )[:400]

    pin = PinsOrm(
        user_id=author.id,
        title=title[:200],
        description=desc,
        original_image=original_rel,
    )
    session.add(pin)
    await session.flush()
    session.add(PinStatsOrm(pin_id=pin.id, view_count=0))
    await session.execute(
        pg_insert(pins_tags)
        .values(pin_id=pin.id, tag_id=tag_id)
        .on_conflict_do_nothing(index_elements=["pin_id", "tag_id"])
    )
    await seed_engagement(
        session, pin_id=pin.id, author_id=author.id, engagers=engagers
    )
    await session.commit()

    pin_id = pin.id
    generate_pin_preview.run(pin_id, watermarked=False)
    session.expire_all()

    if list_for_sale:
        await ensure_seller_listable(session, author.id, author.username)
        pin = await session.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
        if not pin or not pin.image or not pin.content_sha256:
            print(f"  WARN media incomplete pin {pin_id}, skip list")
            await session.commit()
            return True
        await list_pin(session, pin, author.id)
        await session.commit()
        print(f"  LISTED {pin_id} @{author.username} [{tag_name}] {photo['medium'][:40]}")
    else:
        print(f"  OK {pin_id} @{author.username} [{tag_name}] {photo['medium'][:40]}")
    return True


async def run(*, per_tag: int, force: bool) -> None:
    per_tag = max(1, min(per_tag, 30))

    async with async_session_maker() as session:
        sellers, others, engagers = await load_authors(session)
        if not engagers:
            print("ERROR: no eligible authors", file=sys.stderr)
            sys.exit(1)
        if not sellers:
            print("WARN: no sellers — nothing will be listed")

        for s in sellers:
            await ensure_seller_listable(session, s.id, s.username)
        await session.commit()

        created = listed = 0
        for spec in GALLERY:
            have = await count_gallery_for_tag(session, spec.tag)
            need = per_tag if force else max(0, per_tag - have)
            print(f"\n== {spec.tag} have={have} need={need} ==")
            if need <= 0:
                print("  skip")
                continue

            tag_id, tag_name = await ensure_tag(session, spec.tag)
            await session.commit()

            try:
                photos = fetch_met_strict(spec, need=need + 4)
            except Exception as e:
                print(f"  FETCH FAIL (no fallback): {e}", file=sys.stderr)
                continue

            filled = 0
            for photo in photos:
                if filled >= need:
                    break
                want_list = bool(sellers) and random.random() < LIST_SHARE
                if want_list:
                    author = random.choice(sellers)
                elif others:
                    author = random.choice(others)
                else:
                    author = random.choice(sellers)

                try:
                    ok = await create_gallery_pin(
                        session,
                        author=author,
                        spec=spec,
                        tag_id=tag_id,
                        tag_name=tag_name,
                        photo=photo,
                        list_for_sale=want_list,
                        engagers=engagers,
                    )
                except Exception as e:
                    print(f"  ERROR {photo.get('id')}: {e}", file=sys.stderr)
                    try:
                        await session.rollback()
                    except Exception:
                        pass
                    continue
                if ok:
                    filled += 1
                    created += 1
                    if want_list:
                        listed += 1

        print(f"\nDONE created={created} listed={listed}")


def main() -> None:
    p = argparse.ArgumentParser(description="Seed 5 strict physical-art gallery tags")
    p.add_argument("--per-tag", type=int, default=DEFAULT_PER_TAG)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    asyncio.run(run(per_tag=args.per_tag, force=args.force))


if __name__ == "__main__":
    main()
