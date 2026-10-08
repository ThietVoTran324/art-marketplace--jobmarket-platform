"""SQL home-feed ranker: pools → dedupe → score → diversity → page slice."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rest.pins.feed_config import (
    FEED_CANDIDATE_CAP,
    FEED_DIVERSITY_MAX_AUTHOR_STREAK,
    FEED_DIVERSITY_MAX_TAG_STREAK,
    FEED_FRESH_DAYS,
    FEED_GUEST_POOL_RATIOS,
    FEED_POOL_RATIOS,
    FEED_RECENT_DAYS,
    FEED_TRENDING_DAYS,
    INTERACTION_WEIGHTS,
)
from app.postgresql.models import (
    BoardsOrm,
    LikesOrm,
    PinStatsOrm,
    PinsOrm,
    SubsrciptionsOrm,
    board_pins,
    pins_tags,
    users_pins,
    users_view_pins,
)


def _utc_today() -> datetime:
    return datetime.now(timezone.utc)


def _day_seed(user_key: str, day: datetime) -> int:
    raw = f"{user_key}:{day.date().isoformat()}".encode()
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


def _stable_jitter(pin_id: int, seed: int) -> float:
    h = hashlib.sha256(f"{seed}:{pin_id}".encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def _pool_counts(page_size: int, ratios: dict[str, float]) -> dict[str, int]:
    raw = {k: max(0, int(round(page_size * r))) for k, r in ratios.items()}
    total = sum(raw.values())
    if total < page_size and raw:
        # pad largest pool
        top = max(raw, key=raw.get)
        raw[top] += page_size - total
    elif total > page_size and raw:
        top = max(raw, key=raw.get)
        raw[top] = max(0, raw[top] - (total - page_size))
    return raw


async def _fetch_pin_rows(
    db: AsyncSession, pin_ids: list[int]
) -> dict[int, PinsOrm]:
    if not pin_ids:
        return {}
    rows = (
        await db.scalars(select(PinsOrm).where(PinsOrm.id.in_(pin_ids)))
    ).all()
    return {p.id: p for p in rows}


async def _primary_tags(
    db: AsyncSession, pin_ids: list[int]
) -> dict[int, int | None]:
    """Lowest tag_id per pin as a stable 'primary' tag for diversity."""
    if not pin_ids:
        return {}
    rows = await db.execute(
        select(pins_tags.c.pin_id, func.min(pins_tags.c.tag_id)).where(
            pins_tags.c.pin_id.in_(pin_ids)
        ).group_by(pins_tags.c.pin_id)
    )
    return {pid: tid for pid, tid in rows.all()}


async def _recent_exclude_ids(db: AsyncSession, user_id: int) -> set[int]:
    """Saves in last N days + current view rows (views table has no timestamp)."""
    since = _utc_today() - timedelta(days=FEED_RECENT_DAYS)
    out: set[int] = set()

    saved_board = await db.scalars(
        select(board_pins.c.pin_id)
        .join(BoardsOrm, BoardsOrm.id == board_pins.c.board_id)
        .where(BoardsOrm.user_id == user_id, board_pins.c.created_at >= since)
    )
    out.update(saved_board.all())

    saved_direct = await db.scalars(
        select(users_pins.c.pin_id).where(
            users_pins.c.user_id == user_id, users_pins.c.created_at >= since
        )
    )
    out.update(saved_direct.all())

    viewed = await db.scalars(
        select(users_view_pins.c.pin_id).where(users_view_pins.c.user_id == user_id)
    )
    out.update(viewed.all())
    return out


async def _tag_affinity_weights(db: AsyncSession, user_id: int) -> dict[int, float]:
    weights: dict[int, float] = defaultdict(float)
    w = INTERACTION_WEIGHTS

    saved_pins = set(
        (
            await db.scalars(
                select(board_pins.c.pin_id)
                .join(BoardsOrm, BoardsOrm.id == board_pins.c.board_id)
                .where(BoardsOrm.user_id == user_id)
            )
        ).all()
    )
    saved_pins.update(
        (
            await db.scalars(
                select(users_pins.c.pin_id).where(users_pins.c.user_id == user_id)
            )
        ).all()
    )
    liked_pins = set(
        (
            await db.scalars(
                select(LikesOrm.pin_id).where(
                    LikesOrm.user_id == user_id, LikesOrm.pin_id.is_not(None)
                )
            )
        ).all()
    )
    viewed_pins = set(
        (
            await db.scalars(
                select(users_view_pins.c.pin_id).where(
                    users_view_pins.c.user_id == user_id
                )
            )
        ).all()
    )

    async def add_tags(pin_ids: set[int], weight: float) -> None:
        if not pin_ids:
            return
        rows = await db.execute(
            select(pins_tags.c.tag_id).where(pins_tags.c.pin_id.in_(pin_ids))
        )
        for (tag_id,) in rows.all():
            weights[tag_id] += weight

    await add_tags(saved_pins, w["save"])
    await add_tags(liked_pins, w["like"])
    await add_tags(viewed_pins, w["view"])
    return dict(weights)


async def _pool_following(db: AsyncSession, user_id: int, limit: int) -> list[int]:
    if limit <= 0:
        return []
    rows = await db.scalars(
        select(PinsOrm.id)
        .join(SubsrciptionsOrm, SubsrciptionsOrm.following_id == PinsOrm.user_id)
        .where(SubsrciptionsOrm.follower_id == user_id)
        .order_by(desc(PinsOrm.id))
        .limit(limit)
    )
    return list(rows.all())


async def _pool_affinity(
    db: AsyncSession, user_id: int, limit: int, exclude: set[int]
) -> list[int]:
    if limit <= 0:
        return []
    tag_w = await _tag_affinity_weights(db, user_id)
    if not tag_w:
        return []
    tag_ids = list(tag_w.keys())
    # Candidate pins sharing affinity tags
    rows = await db.execute(
        select(pins_tags.c.pin_id, pins_tags.c.tag_id)
        .where(pins_tags.c.tag_id.in_(tag_ids))
        .limit(FEED_CANDIDATE_CAP * 3)
    )
    scores: dict[int, float] = defaultdict(float)
    for pin_id, tag_id in rows.all():
        if pin_id in exclude:
            continue
        scores[pin_id] += tag_w.get(tag_id, 0.0)
    ranked = sorted(scores.items(), key=lambda x: (-x[1], -x[0]))
    return [pid for pid, _ in ranked[:limit]]


async def _pool_fresh(db: AsyncSession, limit: int, exclude: set[int]) -> list[int]:
    if limit <= 0:
        return []
    since = _utc_today() - timedelta(days=FEED_FRESH_DAYS)
    rows = await db.scalars(
        select(PinsOrm.id)
        .where(PinsOrm.created_at >= since)
        .order_by(desc(PinsOrm.id))
        .limit(limit + len(exclude) + 20)
    )
    out = []
    for pid in rows.all():
        if pid in exclude:
            continue
        out.append(pid)
        if len(out) >= limit:
            break
    return out


async def _pool_trending(db: AsyncSession, limit: int, exclude: set[int]) -> list[int]:
    if limit <= 0:
        return []
    since = _utc_today() - timedelta(days=FEED_TRENDING_DAYS)
    rows = await db.execute(
        select(PinsOrm.id, func.coalesce(PinStatsOrm.view_count, 0))
        .outerjoin(PinStatsOrm, PinStatsOrm.pin_id == PinsOrm.id)
        .where(PinsOrm.created_at >= since)
        .order_by(desc(func.coalesce(PinStatsOrm.view_count, 0)), desc(PinsOrm.id))
        .limit(limit + len(exclude) + 20)
    )
    out = []
    for pid, _vc in rows.all():
        if pid in exclude:
            continue
        out.append(pid)
        if len(out) >= limit:
            break
    return out


async def _pool_explore(
    db: AsyncSession, limit: int, exclude: set[int], seed: int
) -> list[int]:
    if limit <= 0:
        return []
    # Pull a window of recent ids then stable-shuffle by day seed
    rows = await db.scalars(
        select(PinsOrm.id).order_by(desc(PinsOrm.id)).limit(FEED_CANDIDATE_CAP)
    )
    ids = [pid for pid in rows.all() if pid not in exclude]
    ids.sort(key=lambda pid: _stable_jitter(pid, seed))
    return ids[:limit]


def _apply_diversity(
    ordered_ids: list[int],
    pins_by_id: dict[int, PinsOrm],
    primary_tag: dict[int, int | None],
) -> list[int]:
    result: list[int] = []
    deferred: list[int] = []
    author_streak = 0
    tag_streak = 0
    last_author: int | None = None
    last_tag: int | None = None

    def try_place(pid: int) -> bool:
        nonlocal author_streak, tag_streak, last_author, last_tag
        pin = pins_by_id.get(pid)
        if not pin:
            return False
        author = pin.user_id
        tag = primary_tag.get(pid)
        next_author_streak = author_streak + 1 if author == last_author else 1
        next_tag_streak = (
            tag_streak + 1 if tag is not None and tag == last_tag else 1
        )
        if next_author_streak > FEED_DIVERSITY_MAX_AUTHOR_STREAK:
            return False
        if tag is not None and next_tag_streak > FEED_DIVERSITY_MAX_TAG_STREAK:
            return False
        result.append(pid)
        author_streak = next_author_streak
        tag_streak = next_tag_streak if tag is not None else 0
        last_author = author
        last_tag = tag
        return True

    for pid in ordered_ids:
        if not try_place(pid):
            deferred.append(pid)

    # Second pass: append deferred when streaks allow
    changed = True
    while deferred and changed:
        changed = False
        still: list[int] = []
        for pid in deferred:
            if try_place(pid):
                changed = True
            else:
                still.append(pid)
        deferred = still

    result.extend(deferred)
    return result


async def build_home_feed_pin_ids(
    db: AsyncSession,
    *,
    user_id: int | None,
    offset: int,
    limit: int,
) -> list[int]:
    """Return ordered pin ids for one page of personalized home."""
    limit = max(1, min(limit, 50))
    offset = max(0, offset)
    day = _utc_today()
    seed = _day_seed(str(user_id) if user_id is not None else "guest", day)

    exclude: set[int] = set()
    if user_id is not None:
        exclude = await _recent_exclude_ids(db, user_id)

    ratios = FEED_POOL_RATIOS if user_id is not None else FEED_GUEST_POOL_RATIOS
    # Build a large candidate list (~cap), then slice — stable for same day seed
    build_size = min(FEED_CANDIDATE_CAP, max(offset + limit + 40, 80))
    counts = _pool_counts(build_size, ratios)

    pool_ids: list[int] = []
    seen: set[int] = set()

    def take(ids: list[int]) -> None:
        for pid in ids:
            if pid in seen:
                continue
            seen.add(pid)
            pool_ids.append(pid)

    if user_id is not None:
        take(await _pool_following(db, user_id, counts.get("following", 0) * 2))
        take(
            await _pool_affinity(
                db, user_id, counts.get("affinity", 0) * 2, exclude | seen
            )
        )
    take(await _pool_explore(db, counts.get("explore", 0) * 2, exclude | seen, seed))
    take(await _pool_trending(db, counts.get("trending", 0) * 2, exclude | seen))
    take(await _pool_fresh(db, counts.get("fresh", 0) * 2, exclude | seen))

    # Fill if thin (cold start)
    if len(pool_ids) < build_size:
        take(await _pool_explore(db, build_size - len(pool_ids), exclude | seen, seed))
    if len(pool_ids) < build_size:
        rows = await db.scalars(
            select(PinsOrm.id).order_by(desc(PinsOrm.id)).limit(build_size + 50)
        )
        take([pid for pid in rows.all() if pid not in exclude])

    # Score: prefer earlier pool order + jitter; hard-exclude recent from first half page0
    hard_exclude = exclude if offset == 0 else set()
    scored: list[tuple[float, int]] = []
    for i, pid in enumerate(pool_ids):
        if pid in hard_exclude and i < build_size // 2:
            # soft: push to end with low score instead of drop entirely when offset>0
            score = -1000.0 + _stable_jitter(pid, seed)
        else:
            # earlier in blend = higher; affinity already ordered inside pool
            score = (len(pool_ids) - i) + _stable_jitter(pid, seed)
            if pid in exclude:
                score -= 50.0  # soft demote recent
        scored.append((score, pid))

    scored.sort(key=lambda x: (-x[0], -x[1]))
    ordered = [pid for _, pid in scored]

    pins_by_id = await _fetch_pin_rows(db, ordered)
    primary = await _primary_tags(db, ordered)
    diversified = _apply_diversity(ordered, pins_by_id, primary)

    page_ids = diversified[offset : offset + limit]
    # If hard-exclude emptied early page, top up from rest
    if offset == 0 and hard_exclude and len(page_ids) < limit:
        for pid in diversified:
            if pid in page_ids:
                continue
            if pid in hard_exclude and len(page_ids) < limit // 2:
                continue
            page_ids.append(pid)
            if len(page_ids) >= limit:
                break

    return page_ids


async def pins_chrono(
    db: AsyncSession, *, offset: int, limit: int
) -> list[PinsOrm]:
    rows = await db.scalars(
        select(PinsOrm)
        .offset(offset)
        .limit(limit)
        .order_by(desc(PinsOrm.id))
    )
    return list(rows.all())
