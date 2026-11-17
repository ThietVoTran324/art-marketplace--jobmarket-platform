"""SQL home-feed ranker.

Guest: popularity on the newest window (like > view > comment > save).
Logged-in: bounded pools (following, affinity, explore, trending, fresh),
time decay, tag rarity, session jitter, then soft diversity.
Ranking is prioritization only — never a keep/delete filter.
"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rest.pins.feed_config import (
    FEED_AFFINITY_DAYS,
    FEED_AFFINITY_TOP_TAGS,
    FEED_AUTHOR_PENALTY,
    FEED_CANDIDATE_CAP,
    FEED_DIVERSITY_MAX_AUTHOR_STREAK,
    FEED_DIVERSITY_MAX_TAG_STREAK,
    FEED_FRESH_DAYS,
    FEED_POOL_RATIOS,
    FEED_RECENT_DAYS,
    FEED_TAG_PENALTY,
    FEED_TRENDING_HOURS,
    GUEST_POPULARITY_WEIGHTS,
    INTERACTION_WEIGHTS,
)
from app.postgresql.models import (
    BoardsOrm,
    CommentsOrm,
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


async def _following_author_ids(db: AsyncSession, user_id: int) -> set[int]:
    rows = await db.scalars(
        select(SubsrciptionsOrm.following_id).where(
            SubsrciptionsOrm.follower_id == user_id
        )
    )
    return set(rows.all())


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


async def _count_map(
    db: AsyncSession, stmt
) -> dict[int, int]:
    rows = await db.execute(stmt)
    return {int(pid): int(cnt or 0) for pid, cnt in rows.all()}


async def _engagement_maps(
    db: AsyncSession, candidate_ids: list[int]
) -> dict[str, dict[int, int]]:
    """Batch like / view / comment / save counts for guest popularity."""
    if not candidate_ids:
        return {"like": {}, "view": {}, "comment": {}, "save": {}}

    likes = await _count_map(
        db,
        select(LikesOrm.pin_id, func.count())
        .where(LikesOrm.pin_id.in_(candidate_ids))
        .group_by(LikesOrm.pin_id),
    )
    views = await _view_counts(db, candidate_ids)
    comments = await _count_map(
        db,
        select(CommentsOrm.pin_id, func.count())
        .where(
            CommentsOrm.pin_id.in_(candidate_ids),
            CommentsOrm.comment_id.is_(None),  # top-level only
        )
        .group_by(CommentsOrm.pin_id),
    )
    # Save ≈ profile saves + board saves (row counts; fine for ranking)
    profile_saves = await _count_map(
        db,
        select(users_pins.c.pin_id, func.count())
        .where(users_pins.c.pin_id.in_(candidate_ids))
        .group_by(users_pins.c.pin_id),
    )
    board_saves = await _count_map(
        db,
        select(board_pins.c.pin_id, func.count())
        .where(board_pins.c.pin_id.in_(candidate_ids))
        .group_by(board_pins.c.pin_id),
    )
    saves: dict[int, int] = defaultdict(int)
    for pid, c in profile_saves.items():
        saves[pid] += c
    for pid, c in board_saves.items():
        saves[pid] += c

    return {
        "like": likes,
        "view": views,
        "comment": comments,
        "save": dict(saves),
    }


def _guest_popularity_score(
    pid: int,
    *,
    engagement: dict[str, dict[int, int]],
    seed: int,
    recency_rank: float,
) -> float:
    w = GUEST_POPULARITY_WEIGHTS
    score = 0.0
    score += w["like"] * math.log1p(engagement["like"].get(pid, 0))
    score += w["view"] * math.log1p(engagement["view"].get(pid, 0))
    score += w["comment"] * math.log1p(engagement["comment"].get(pid, 0))
    score += w["save"] * math.log1p(engagement["save"].get(pid, 0))
    # Tiny stable jitter + slight recency so ties are not arbitrary / frozen
    score += _stable_jitter(pid, seed) * 0.01
    score += recency_rank * 0.001
    return score


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


def _pool_take(cap: int, key: str) -> int:
    return max(8, int(cap * FEED_POOL_RATIOS.get(key, 0.1)))


async def _ids(db: AsyncSession, stmt) -> list[int]:
    return list((await db.scalars(stmt)).all())


async def _top_affinity_tags(db: AsyncSession, user_id: int) -> dict[int, float]:
    """Save/like/view tag weights. Saves respect the 90-day window (they have timestamps)."""
    weights: dict[int, float] = defaultdict(float)
    w = INTERACTION_WEIGHTS
    since = _utc_today() - timedelta(days=FEED_AFFINITY_DAYS)

    saved: set[int] = set(
        (
            await db.scalars(
                select(board_pins.c.pin_id)
                .join(BoardsOrm, BoardsOrm.id == board_pins.c.board_id)
                .where(BoardsOrm.user_id == user_id, board_pins.c.created_at >= since)
            )
        ).all()
    )
    saved.update(
        (
            await db.scalars(
                select(users_pins.c.pin_id).where(
                    users_pins.c.user_id == user_id,
                    users_pins.c.created_at >= since,
                )
            )
        ).all()
    )
    liked: set[int] = set(
        (
            await db.scalars(
                select(LikesOrm.pin_id)
                .where(LikesOrm.user_id == user_id, LikesOrm.pin_id.is_not(None))
                .limit(200)
            )
        ).all()
    )
    viewed: set[int] = set(
        (
            await db.scalars(
                select(users_view_pins.c.pin_id)
                .where(users_view_pins.c.user_id == user_id)
                .limit(80)
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

    await add_tags(saved, w["save"])
    await add_tags(liked, w["like"])
    await add_tags(viewed, w["view"])
    ranked = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)
    return dict(ranked[:FEED_AFFINITY_TOP_TAGS])


async def _tag_idf(db: AsyncSession, tag_ids: list[int]) -> dict[int, float]:
    if not tag_ids:
        return {}
    rows = await db.execute(
        select(pins_tags.c.tag_id, func.count())
        .where(pins_tags.c.tag_id.in_(tag_ids))
        .group_by(pins_tags.c.tag_id)
    )
    return {int(tid): 1.0 / math.log(1.0 + int(cnt or 1)) for tid, cnt in rows.all()}


async def _login_candidate_ids(
    db: AsyncSession,
    *,
    user_id: int,
    day: datetime,
    top_tags: dict[int, float],
) -> list[int]:
    """Union of bounded SQL pools. Not the newest-N window."""
    cap = FEED_CANDIDATE_CAP
    picked: list[int] = []
    following = await _following_author_ids(db, user_id)
    if following:
        picked += await _ids(
            db,
            select(PinsOrm.id)
            .where(PinsOrm.user_id.in_(following))
            .order_by(desc(PinsOrm.id))
            .limit(_pool_take(cap, "following")),
        )

    tag_ids = list(top_tags.keys())
    if tag_ids:
        since_aff = day - timedelta(days=FEED_AFFINITY_DAYS)
        picked += await _ids(
            db,
            select(PinsOrm.id)
            .join(pins_tags, pins_tags.c.pin_id == PinsOrm.id)
            .where(pins_tags.c.tag_id.in_(tag_ids), PinsOrm.created_at >= since_aff)
            .group_by(PinsOrm.id)
            .order_by(desc(func.count()), desc(PinsOrm.id))
            .limit(_pool_take(cap, "affinity")),
        )
        explore_n = _pool_take(cap, "explore")
        primary = (
            select(
                pins_tags.c.pin_id.label("pin_id"),
                func.min(pins_tags.c.tag_id).label("primary_tag"),
            )
            .group_by(pins_tags.c.pin_id)
            .subquery()
        )
        picked += await _ids(
            db,
            select(PinsOrm.id)
            .join(primary, primary.c.pin_id == PinsOrm.id)
            .outerjoin(PinStatsOrm, PinStatsOrm.pin_id == PinsOrm.id)
            .where(primary.c.primary_tag.not_in(tag_ids))
            .order_by(desc(PinStatsOrm.view_count).nulls_last(), desc(PinsOrm.id))
            .limit(explore_n),
        )

    since_trend = day - timedelta(hours=FEED_TRENDING_HOURS)
    picked += await _ids(
        db,
        select(PinsOrm.id)
        .where(PinsOrm.created_at >= since_trend)
        .order_by(desc(PinsOrm.id))
        .limit(_pool_take(cap, "trending")),
    )
    since_fresh = day - timedelta(days=FEED_FRESH_DAYS)
    picked += await _ids(
        db,
        select(PinsOrm.id)
        .where(PinsOrm.created_at >= since_fresh)
        .order_by(desc(PinsOrm.id))
        .limit(_pool_take(cap, "fresh")),
    )

    unique = list(dict.fromkeys(picked))
    if len(unique) < 40:
        unique += await _ids(
            db,
            select(PinsOrm.id).order_by(desc(PinsOrm.id)).limit(cap),
        )
        unique = list(dict.fromkeys(unique))
    return unique[:cap]


def _apply_diversity_scored(
    scored: list[tuple[float, int]],
    pins_by_id: dict[int, PinsOrm],
    primary_tag: dict[int, int | None],
) -> list[int]:
    """Greedy pick with author/tag penalties; hard streak caps still apply."""
    remaining = list(scored)
    result: list[int] = []
    author_streak = 0
    tag_streak = 0
    last_author: int | None = None
    last_tag: int | None = None

    while remaining:
        best_i: int | None = None
        best_adj: float | None = None
        best_meta: tuple[int | None, int | None, int, int] | None = None
        window = remaining[:150]
        for i, (sc, pid) in enumerate(window):
            pin = pins_by_id.get(pid)
            author = pin.user_id if pin is not None else None
            tag = primary_tag.get(pid)
            adj = sc
            if author is not None and author == last_author:
                adj -= FEED_AUTHOR_PENALTY
            if tag is not None and tag == last_tag:
                adj -= FEED_TAG_PENALTY
            next_author = author_streak + 1 if author is not None and author == last_author else 1
            next_tag = tag_streak + 1 if tag is not None and tag == last_tag else 1
            if next_author > FEED_DIVERSITY_MAX_AUTHOR_STREAK:
                continue
            if tag is not None and next_tag > FEED_DIVERSITY_MAX_TAG_STREAK:
                continue
            if best_adj is None or adj > best_adj:
                best_adj = adj
                best_i = i
                best_meta = (author, tag, next_author, next_tag if tag is not None else 0)
        if best_i is None:
            result.extend(pid for _, pid in remaining)
            break
        _, pid = remaining.pop(best_i)
        result.append(pid)
        assert best_meta is not None
        last_author, last_tag, author_streak, tag_streak = best_meta
    return result


async def _idf_affinity(
    db: AsyncSession,
    top_tags: dict[int, float],
    idf: dict[int, float],
    pin_ids: list[int],
) -> dict[int, float]:
    if not top_tags or not pin_ids:
        return {}
    rows = await db.execute(
        select(pins_tags.c.pin_id, pins_tags.c.tag_id).where(
            pins_tags.c.pin_id.in_(pin_ids),
            pins_tags.c.tag_id.in_(list(top_tags)),
        )
    )
    out: dict[int, float] = defaultdict(float)
    for pid, tid in rows.all():
        out[int(pid)] += float(top_tags.get(int(tid), 0.0)) * float(idf.get(int(tid), 1.0))
    return out


async def build_home_feed_pin_ids(
    db: AsyncSession,
    *,
    user_id: int | None,
    offset: int,
    limit: int,
    feed_nonce: str | None = None,
) -> list[int]:
    """Ordered pin ids for one home page.

    Guest stays on the newest window and popularity. Login uses bounded pools.
    `feed_nonce` only changes login jitter; guest ignores it.
    """
    limit = max(1, min(limit, 50))
    offset = max(0, offset)
    day = _utc_today()

    if user_id is None:
        seed = _day_seed("guest", day)
        window = max(FEED_CANDIDATE_CAP, offset + limit)
        candidates = list(
            (
                await db.scalars(
                    select(PinsOrm.id).order_by(desc(PinsOrm.id)).limit(window)
                )
            ).all()
        )
        if not candidates:
            return []
        pins_by_id = await _fetch_pin_rows(db, candidates)
        engagement = await _engagement_maps(db, candidates)
        scored: list[tuple[float, int]] = []
        n = len(candidates)
        for i, pid in enumerate(candidates):
            scored.append(
                (
                    _guest_popularity_score(
                        pid,
                        engagement=engagement,
                        seed=seed,
                        recency_rank=float(n - i),
                    ),
                    pid,
                )
            )
        scored.sort(key=lambda x: (-x[0], -x[1]))
        ordered = [pid for _, pid in scored]
        primary = await _primary_tags(db, ordered)
        diversified = _apply_diversity(ordered, pins_by_id, primary)
        return diversified[offset : offset + limit]

    nonce = (feed_nonce or "").strip()[:64]
    seed = _day_seed(f"{user_id}:{nonce}" if nonce else str(user_id), day)
    top_tags = await _top_affinity_tags(db, user_id)
    candidates = await _login_candidate_ids(db, user_id=user_id, day=day, top_tags=top_tags)
    if not candidates:
        return []

    pins_by_id = await _fetch_pin_rows(db, candidates)
    view_counts = await _view_counts(db, candidates)
    following_authors = await _following_author_ids(db, user_id)
    idf = await _tag_idf(db, list(top_tags))
    affinity = await _idf_affinity(db, top_tags, idf, candidates)
    demote_saves = await _recent_save_ids(db, user_id)
    demote_views = await _view_ids(db, user_id)

    rates: dict[int, float] = {}
    for pid in candidates:
        pin = pins_by_id.get(pid)
        if pin is None or pin.created_at is None:
            continue
        created = pin.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        hours = max(0.0, (day - created).total_seconds() / 3600.0)
        if hours <= FEED_TRENDING_HOURS:
            rates[pid] = view_counts.get(pid, 0) / max(1.0, hours)
    max_rate = max(rates.values(), default=0.0) or 1.0

    scored_login: list[tuple[float, int]] = []
    for pid in candidates:
        score = _stable_jitter(pid, seed)
        pin = pins_by_id.get(pid)
        if pin is not None:
            if pin.user_id in following_authors:
                score += 40.0
            created = pin.created_at
            if created is not None:
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                hours = max(0.0, (day - created).total_seconds() / 3600.0)
                score += 20.0 / ((1.0 + hours) ** 0.35)
                if pid in rates:
                    score += 8.0 * (rates[pid] / max_rate)
        score += min(30.0, affinity.get(pid, 0.0) * 2.0)
        if pid in demote_saves:
            score -= 15.0
        elif pid in demote_views:
            score -= 5.0
        scored_login.append((score, pid))

    scored_login.sort(key=lambda x: (-x[0], -x[1]))
    primary = await _primary_tags(db, [pid for _, pid in scored_login])
    diversified = _apply_diversity_scored(scored_login, pins_by_id, primary)
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
