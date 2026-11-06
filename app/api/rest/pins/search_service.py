"""Feed search Wave1: Enter-only pin lookup via tag/author index (no full pin scan).

Free-text resolve uses the same exact → prefix → contains ranking as the old
keyword suggest catalog, then returns pins ordered by best tag match quality.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rest.text_normalize import fold_search_text
from app.api.rest.users.preferences import is_profile_discoverable
from app.postgresql.models import PinsOrm, TagsOrm, UsersOrm, pins_tags
from app.redis.redis_cache import redis_connection

SEARCH_Q_MAX = 100
SUGGEST_LIMIT_DEFAULT = 10
MATCHING_TAGS_LIMIT = 12
CACHE_TTL_KW = 60
CACHE_TTL_PINS = 45

# Higher = closer match (mirrors former L1 suggest ranking).
_RANK_EXACT = 300
_RANK_PREFIX = 200
_RANK_CONTAINS = 100


def _tag_match_rank(name_fold: str, needle: str) -> int:
    if not needle or not name_fold:
        return 0
    if name_fold == needle:
        return _RANK_EXACT
    if name_fold.startswith(needle):
        return _RANK_PREFIX
    if len(needle) >= 2 and needle in name_fold:
        return _RANK_CONTAINS
    return 0


def _cap_q(raw: str) -> str:
    return (raw or "").strip()[:SEARCH_Q_MAX]


async def _cache_get(key: str) -> Any | None:
    if not redis_connection:
        return None
    try:
        raw = await redis_connection.get(key)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return None


async def _cache_set(key: str, value: Any, ttl: int) -> None:
    if not redis_connection:
        return
    try:
        await redis_connection.set(key, json.dumps(value), ex=ttl)
    except Exception:  # noqa: BLE001
        return


async def invalidate_tag_search_cache(tag_id: int | None = None) -> None:
    """Best-effort; prefix delete if Redis supports SCAN."""
    if not redis_connection:
        return
    try:
        patterns = [
            "search:kw:v1:*",
            "search:kw:v2:*",
            "search:resolve:v1:*",
            "search:pins:tags:*",
        ]
        if tag_id is not None:
            patterns.append(f"search:pins:tag:{tag_id}:*")
        else:
            patterns.append("search:pins:tag:*")
        for pattern in patterns:
            async for key in redis_connection.scan_iter(match=pattern, count=100):
                await redis_connection.delete(key)
    except Exception:  # noqa: BLE001
        return


async def invalidate_author_search_cache(user_id: int) -> None:
    if not redis_connection:
        return
    try:
        pattern = f"search:pins:author:{user_id}:*"
        async for key in redis_connection.scan_iter(match=pattern, count=100):
            await redis_connection.delete(key)
    except Exception:  # noqa: BLE001
        return


async def suggest_keywords(
    db: AsyncSession,
    *,
    q: str,
    limit: int = SUGGEST_LIMIT_DEFAULT,
    exclude_user_id: int | None = None,
) -> list[dict[str, Any]]:
    """L1: tags (+ discoverable authors). Never scans pins."""
    qn = _cap_q(q)
    needle = fold_search_text(qn)
    if not needle:
        return []

    cache_key = f"search:kw:v2:{needle}:{limit}"
    cached = await _cache_get(cache_key)
    if isinstance(cached, list):
        return cached[:limit]

    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Exact → prefix → contains (len>=2). 1 char = prefix only (less noise).
    match_clause = or_(
        TagsOrm.name_fold == needle,
        TagsOrm.name_fold.like(f"{needle}%"),
    )
    if len(needle) >= 2:
        match_clause = or_(match_clause, TagsOrm.name_fold.like(f"%{needle}%"))

    tag_rows = (
        await db.execute(
            select(TagsOrm.id, TagsOrm.name, TagsOrm.name_fold)
            .where(TagsOrm.name_fold != "everything", match_clause)
            .order_by(
                (TagsOrm.name_fold == needle).desc(),
                TagsOrm.name_fold.like(f"{needle}%").desc(),
                TagsOrm.name_fold.asc(),
            )
            .limit(limit)
        )
    ).all()
    for tid, name, _fold in tag_rows:
        key = f"tag:{tid}"
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "type": "tag",
                "id": tid,
                "label": name,
                "tag_id": tid,
                "author_id": None,
            }
        )

    remaining = max(0, limit - len(out))
    if remaining and len(needle) >= 2:
        # Username prefix (fold in Python after fetch — username index via ILIKE prefix)
        users = (
            await db.scalars(
                select(UsersOrm)
                .where(UsersOrm.username.ilike(f"{qn}%"))
                .order_by(UsersOrm.username.asc())
                .limit(remaining * 3)
            )
        ).all()
        for user in users:
            if exclude_user_id is not None and user.id == exclude_user_id:
                continue
            if not is_profile_discoverable(user):
                continue
            ufold = fold_search_text(user.username)
            if not (ufold == needle or ufold.startswith(needle)):
                continue
            key = f"author:{user.id}"
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "type": "author",
                    "id": user.id,
                    "label": user.username,
                    "tag_id": None,
                    "author_id": user.id,
                }
            )
            if len(out) >= limit:
                break

    await _cache_set(cache_key, out, CACHE_TTL_KW)
    return out[:limit]


async def _matching_tags_ranked(
    db: AsyncSession, needle: str, *, limit: int = MATCHING_TAGS_LIMIT
) -> list[tuple[int, int]]:
    """Return [(tag_id, rank)] exact → prefix → contains. Redis-warmed (ids+ranks only)."""
    if not needle:
        return []
    cache_key = f"search:resolve:v1:{needle}:{limit}"
    cached = await _cache_get(cache_key)
    if isinstance(cached, list):
        out_cached: list[tuple[int, int]] = []
        for item in cached:
            if (
                isinstance(item, (list, tuple))
                and len(item) == 2
                and str(item[0]).isdigit()
            ):
                out_cached.append((int(item[0]), int(item[1])))
        if out_cached or cached == []:
            return out_cached

    match_clause = or_(
        TagsOrm.name_fold == needle,
        TagsOrm.name_fold.like(f"{needle}%"),
    )
    if len(needle) >= 2:
        match_clause = or_(match_clause, TagsOrm.name_fold.like(f"%{needle}%"))
    rows = (
        await db.execute(
            select(TagsOrm.id, TagsOrm.name_fold)
            .where(TagsOrm.name_fold != "everything", match_clause)
            .order_by(
                (TagsOrm.name_fold == needle).desc(),
                TagsOrm.name_fold.like(f"{needle}%").desc(),
                TagsOrm.name_fold.asc(),
            )
            .limit(limit)
        )
    ).all()
    out: list[tuple[int, int]] = []
    for tid, name_fold in rows:
        rank = _tag_match_rank(name_fold or "", needle)
        if rank <= 0:
            continue
        out.append((int(tid), rank))
    await _cache_set(cache_key, [[tid, rank] for tid, rank in out], CACHE_TTL_KW)
    return out


async def resolve_search_target(
    db: AsyncSession,
    *,
    value: str | None,
    tag_id: int | None,
    author_id: int | None,
) -> dict[str, Any]:
    """
    Explicit ids win; else free-text → ranked tags (exact→prefix→contains) → pins.
    Exact discoverable username only when no tag matches. No full pin text scan.
    """
    if tag_id is not None:
        tag = await db.scalar(select(TagsOrm).where(TagsOrm.id == tag_id))
        if tag is None:
            return {"kind": "none", "reason": "no_match"}
        return {"kind": "tag", "tag_id": tag.id, "label": tag.name}

    if author_id is not None:
        user = await db.scalar(select(UsersOrm).where(UsersOrm.id == author_id))
        if user is None or not is_profile_discoverable(user):
            return {"kind": "none", "reason": "no_match"}
        return {"kind": "author", "author_id": user.id, "label": user.username}

    qn = _cap_q(value or "")
    needle = fold_search_text(qn)
    if not needle:
        return {"kind": "none", "reason": "empty"}

    ranked = await _matching_tags_ranked(db, needle, limit=MATCHING_TAGS_LIMIT)
    if ranked:
        return {
            "kind": "tags",
            "tag_ids": [tid for tid, _ in ranked],
            "tag_ranks": {str(tid): rank for tid, rank in ranked},
            "needle": needle,
            "label": qn,
        }

    # Exact username (case/diacritic insensitive via fold compare)
    candidates = (
        await db.scalars(
            select(UsersOrm).where(UsersOrm.username.ilike(qn)).limit(20)
        )
    ).all()
    for user in candidates:
        if fold_search_text(user.username) != needle:
            continue
        if not is_profile_discoverable(user):
            continue
        return {"kind": "author", "author_id": user.id, "label": user.username}

    return {"kind": "none", "reason": "no_match"}


async def _pins_by_ids_ordered(db: AsyncSession, ids: list[int]) -> list[PinsOrm]:
    if not ids:
        return []
    pins = (await db.scalars(select(PinsOrm).where(PinsOrm.id.in_(ids)))).all()
    by_id = {p.id: p for p in pins}
    return [by_id[i] for i in ids if i in by_id]


async def list_pins_for_target(
    db: AsyncSession,
    *,
    target: dict[str, Any],
    offset: int,
    limit: int,
) -> list[PinsOrm]:
    kind = target.get("kind")
    if kind == "tag":
        tid = int(target["tag_id"])
        cache_key = f"search:pins:tag:{tid}:{offset}:{limit}"
        cached = await _cache_get(cache_key)
        if isinstance(cached, list):
            return await _pins_by_ids_ordered(db, cached)

        rows = (
            await db.scalars(
                select(PinsOrm)
                .join(pins_tags, pins_tags.c.pin_id == PinsOrm.id)
                .where(pins_tags.c.tag_id == tid)
                .order_by(desc(PinsOrm.id))
                .offset(offset)
                .limit(limit)
            )
        ).all()
        await _cache_set(cache_key, [p.id for p in rows], CACHE_TTL_PINS)
        return list(rows)

    if kind == "tags":
        tag_ids = [int(x) for x in (target.get("tag_ids") or []) if x is not None]
        if not tag_ids:
            return []
        raw_ranks = target.get("tag_ranks") or {}
        tag_ranks = {
            int(k): int(v)
            for k, v in raw_ranks.items()
            if str(k).isdigit() and int(k) in tag_ids
        }
        # Stable cache key includes rank map so exact→similar order stays consistent.
        rank_part = ",".join(
            f"{tid}:{tag_ranks.get(tid, 0)}" for tid in sorted(tag_ids)
        )
        cache_key = f"search:pins:tags:v2:{rank_part}:{offset}:{limit}"
        cached = await _cache_get(cache_key)
        if isinstance(cached, list):
            return await _pins_by_ids_ordered(db, cached)

        rank_expr = case(
            {tid: rank for tid, rank in tag_ranks.items()},
            value=pins_tags.c.tag_id,
            else_=0,
        )
        best_rank = func.max(rank_expr).label("best_rank")
        id_rows = (
            await db.execute(
                select(PinsOrm.id, best_rank)
                .join(pins_tags, pins_tags.c.pin_id == PinsOrm.id)
                .where(pins_tags.c.tag_id.in_(tag_ids))
                .group_by(PinsOrm.id)
                .order_by(desc(best_rank), desc(PinsOrm.id))
                .offset(offset)
                .limit(limit)
            )
        ).all()
        ids = [int(r[0]) for r in id_rows]
        uniq = await _pins_by_ids_ordered(db, ids)
        await _cache_set(cache_key, ids, CACHE_TTL_PINS)
        return uniq

    if kind == "author":
        uid = int(target["author_id"])
        cache_key = f"search:pins:author:{uid}:{offset}:{limit}"
        cached = await _cache_get(cache_key)
        if isinstance(cached, list):
            return await _pins_by_ids_ordered(db, cached)

        rows = (
            await db.scalars(
                select(PinsOrm)
                .where(PinsOrm.user_id == uid)
                .order_by(desc(PinsOrm.id))
                .offset(offset)
                .limit(limit)
            )
        ).all()
        await _cache_set(cache_key, [p.id for p in rows], CACHE_TTL_PINS)
        return list(rows)

    return []
