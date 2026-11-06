"""Batch feed-card meta (username / likes / comments / liked).

Safe to attach onto search responses per-request. Do not Redis-cache `liked`
under a shared query key — only pin id lists stay in search cache.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.postgresql.models import CommentsOrm, LikesOrm, PinsOrm, UsersOrm

from .schemas import FeedMetaOut


async def build_feed_meta(
    db: AsyncSession,
    pin_ids: list[int],
    *,
    user_id: int | None,
    max_ids: int = 50,
) -> list[FeedMetaOut]:
    seen: set[int] = set()
    ids: list[int] = []
    for pid in pin_ids:
        if not isinstance(pid, int) or pid <= 0 or pid in seen:
            continue
        seen.add(pid)
        ids.append(pid)
        if len(ids) >= max_ids:
            break
    if not ids:
        return []

    pins = (await db.scalars(select(PinsOrm).where(PinsOrm.id.in_(ids)))).all()
    pin_by_id = {p.id: p for p in pins}
    owner_ids = {p.user_id for p in pins}
    users = (
        (await db.scalars(select(UsersOrm).where(UsersOrm.id.in_(owner_ids)))).all()
        if owner_ids
        else []
    )
    username_by_uid = {u.id: u.username for u in users}

    likes_rows = (
        await db.execute(
            select(LikesOrm.pin_id, func.count())
            .where(LikesOrm.pin_id.in_(ids))
            .group_by(LikesOrm.pin_id)
        )
    ).all()
    likes_by_pin = {row[0]: int(row[1]) for row in likes_rows}

    liked_ids: set[int] = set()
    if user_id is not None:
        liked_ids = set(
            (
                await db.scalars(
                    select(LikesOrm.pin_id).where(
                        LikesOrm.user_id == user_id,
                        LikesOrm.pin_id.in_(ids),
                    )
                )
            ).all()
        )

    comments_rows = (
        await db.execute(
            select(CommentsOrm.pin_id, func.count())
            .where(CommentsOrm.pin_id.in_(ids))
            .group_by(CommentsOrm.pin_id)
        )
    ).all()
    comments_by_pin = {row[0]: int(row[1]) for row in comments_rows}

    out: list[FeedMetaOut] = []
    for pid in ids:
        pin = pin_by_id.get(pid)
        if pin is None:
            continue
        out.append(
            FeedMetaOut(
                pin_id=pid,
                username=username_by_uid.get(pin.user_id),
                likes_count=likes_by_pin.get(pid, 0),
                liked=pid in liked_ids,
                comments_count=comments_by_pin.get(pid, 0),
            )
        )
    return out


def meta_by_pin_id(rows: list[FeedMetaOut]) -> dict[int, FeedMetaOut]:
    return {r.pin_id: r for r in rows}
