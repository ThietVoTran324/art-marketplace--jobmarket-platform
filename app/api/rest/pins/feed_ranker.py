"""SQL home-feed ranker: chrono universe → score boost/demote → diversity reorder → page.

Ranking is prioritization only — never a keep/delete filter. Missing affinity,
views, or follows must not empty the feed; cold start == chrono order with jitter.
"""

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
        select(pins_tags.c.pin_id, func.min(pins_tags.c.tag_id))
        .where(pins_tags.c.pin_id.in_(pin_ids))
        .group_by(pins_tags.c.pin_id)
    )
    return {pid: tid for pid, tid in rows.all()}


async def _recent_save_ids(db: AsyncSession, user_id: int) -> set[int]:
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
    return out


async def _view_ids(db: AsyncSession, user_id: int, cap: int = 80) -> set[int]:
    rows = await db.scalars(
        select(users_view_pins.c.pin_id)
        .where(users_view_pins.c.user_id == user_id)
        .limit(cap)
    )
    return set(rows.all())


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


async def _following_author_ids(db: AsyncSession, user_id: int) -> set[int]:
    rows = await db.scalars(
        select(SubsrciptionsOrm.following_id).where(
            SubsrciptionsOrm.follower_id == user_id
        )
    )
    return set(rows.all())


async def _pin_affinity_scores(
    db: AsyncSession, user_id: int, candidate_ids: list[int]
) -> dict[int, float]:
    """Boost scores for candidates sharing affinity tags. Never drops pins."""
    if not candidate_ids:
        return {}
    tag_w = await _tag_affinity_weights(db, user_id)
    if not tag_w:
        return {}
    rows = await db.execute(
        select(pins_tags.c.pin_id, pins_tags.c.tag_id).where(
            pins_tags.c.pin_id.in_(candidate_ids),
            pins_tags.c.tag_id.in_(list(tag_w.keys())),
        )
    )
    scores: dict[int, float] = defaultdict(float)
    for pin_id, tag_id in rows.all():
        scores[pin_id] += tag_w.get(tag_id, 0.0)
    return dict(scores)


async def _view_counts(
    db: AsyncSession, candidate_ids: list[int]
) -> dict[int, int]:
    if not candidate_ids:
        return {}
    rows = await db.execute(
        select(PinStatsOrm.pin_id, PinStatsOrm.view_count).where(
            PinStatsOrm.pin_id.in_(candidate_ids)
        )
    )
    return {pid: int(vc or 0) for pid, vc in rows.all()}


def _apply_diversity(
    ordered_ids: list[int],
    pins_by_id: dict[int, PinsOrm],
    primary_tag: dict[int, int | None],
) -> list[int]:
    """Reorder for author/tag streaks — append leftovers; never drop."""
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
            # Keep unknown ids at end rather than lose them
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
    """Ordered pin ids for one home page.

    Universe = newest FEED_CANDIDATE_CAP pins (same catalog chrono uses).
    Personalization only reorders that universe.
    """
    limit = max(1, min(limit, 50))
    offset = max(0, offset)
    day = _utc_today()
    seed = _day_seed(str(user_id) if user_id is not None else "guest", day)

    # 1) Candidate universe — always chrono window; never filtered by user history.
    # Grow window so deep pages still have ids (pagination ≠ filter).
    window = max(FEED_CANDIDATE_CAP, offset + limit)
    candidates = list(
        (
            await db.scalars(
                select(PinsOrm.id)
                .order_by(desc(PinsOrm.id))
                .limit(window)
            )
        ).all()
    )
    if not candidates:
        return []

    pins_by_id = await _fetch_pin_rows(db, candidates)
    view_counts = await _view_counts(db, candidates)

    following_authors: set[int] = set()
    affinity: dict[int, float] = {}
    demote_saves: set[int] = set()
    demote_views: set[int] = set()
    if user_id is not None:
        following_authors = await _following_author_ids(db, user_id)
        affinity = await _pin_affinity_scores(db, user_id, candidates)
        demote_saves = await _recent_save_ids(db, user_id)
        demote_views = await _view_ids(db, user_id)

    fresh_since = day - timedelta(days=FEED_FRESH_DAYS)
    trending_since = day - timedelta(days=FEED_TRENDING_DAYS)
    max_views = max(view_counts.values(), default=0) or 1

    # 2) Score every candidate (boost / soft demote). No removals.
    scored: list[tuple[float, int]] = []
    for i, pid in enumerate(candidates):
        # Recency base: newer pins slightly ahead; jitter breaks ties stably
        score = (len(candidates) - i) * 0.01 + _stable_jitter(pid, seed)

        pin = pins_by_id.get(pid)
        if pin is not None:
            if pin.user_id in following_authors:
                score += 40.0
            created = pin.created_at
            if created is not None:
                # normalize aware/naive
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if created >= fresh_since:
                    score += 12.0
                if created >= trending_since:
                    score += 8.0 * (view_counts.get(pid, 0) / max_views)

        score += min(30.0, affinity.get(pid, 0.0) * 2.0)

        if pid in demote_saves:
            score -= 15.0
        elif pid in demote_views:
            score -= 5.0

        scored.append((score, pid))

    scored.sort(key=lambda x: (-x[0], -x[1]))
    ordered = [pid for _, pid in scored]

    primary = await _primary_tags(db, ordered)
    diversified = _apply_diversity(ordered, pins_by_id, primary)

    # 3) Page slice — if offset past universe, empty (same as chrono exhaustion)
    return diversified[offset : offset + limit]


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
