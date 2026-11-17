import math
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import desc, func, insert, select

from app.api.rest.dependencies import db, filter, user_id
from app.api.rest.pins.pin_out import pins_out
from app.api.rest.pins.schemas import PinOut
from app.api.rest.pins.search_service import invalidate_tag_search_cache
from app.api.rest.text_normalize import fold_search_text
from app.config import settings
from app.postgresql.models import (
    LikesOrm,
    PinStatsOrm,
    PinsOrm,
    TagsOrm,
    board_pins,
    pins_tags,
)

from .schemas import TagOut, TagsIn

mimetypes.add_type("image/webp", ".webp")

router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_tags_on_pin(db: db, user_id: user_id, tags_model: TagsIn):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == tags_model.pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    from app.ai.rag.hooks import enqueue_rag_pin, enqueue_rag_tag

    for tag_name in tags_model.tags:
        tag = await db.scalar(select(TagsOrm).where(TagsOrm.name == tag_name))
        if not tag:
            new_tag = await db.scalar(
                insert(TagsOrm)
                .values(name=tag_name, name_fold=fold_search_text(tag_name)[:100])
                .returning(TagsOrm)
            )
            await db.execute(insert(pins_tags).values(pin_id=pin.id, tag_id=new_tag.id))
            await db.commit()
            await invalidate_tag_search_cache(new_tag.id)
            enqueue_rag_tag(new_tag.id)
        else:
            await db.execute(insert(pins_tags).values(pin_id=pin.id, tag_id=tag.id))
            await db.commit()
            await invalidate_tag_search_cache(tag.id)
    enqueue_rag_pin(pin.id)


@router.get("/", response_model=list[TagOut])
async def get_all_tags(db: db, user_id: user_id):
    tags = await db.scalars(select(TagsOrm))
    return tags


@router.get("/tags-with-first-pin", response_model=list[dict])
async def get_tags_with_first_pin(user_id: user_id, db: db):
    """Full tag catalog (name + pin_count + sample pinId), hottest first.

    Home bar only *renders* top-N; FE keeps full list for search chips / deep links.
    """
    result = []

    last_pin = await db.scalar(select(PinsOrm).order_by(desc(PinsOrm.id)).limit(1))
    result.append(
        {
            "id": 0,
            "name": "Everything",
            "pinId": last_pin.id if last_pin else None,
            "pin_count": 0,
        }
    )

    stats = (
        select(
            pins_tags.c.tag_id.label("tag_id"),
            func.count().label("pin_count"),
            func.min(pins_tags.c.pin_id).label("pin_id"),
        )
        .group_by(pins_tags.c.tag_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(TagsOrm.id, TagsOrm.name, stats.c.pin_count, stats.c.pin_id)
            .join(stats, stats.c.tag_id == TagsOrm.id)
            .order_by(desc(stats.c.pin_count), TagsOrm.name.asc())
        )
    ).all()
    for tid, name, pin_count, pin_id in rows:
        result.append(
            {
                "id": int(tid),
                "name": name,
                "pinId": int(pin_id) if pin_id is not None else None,
                "pin_count": int(pin_count or 0),
            }
        )

    return result




@router.get("/tags-with-first-pin/upload/{id}")
async def get_image(user_id: user_id, id: int, db: db):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    media_root = Path(settings.MEDIA_PATH)

    # fallback
    default_image = media_root / "notauth" / "1.jpg"

    # 👉 VIDEO
    if pin.videoPreview:
        video_path = media_root / pin.videoPreview
        if video_path.exists():
            return FileResponse(video_path, media_type="video/mp4")

        return FileResponse(default_image, media_type="image/jpeg")

    # 👉 IMAGE
    if not pin.image:
        return FileResponse(default_image, media_type="image/jpeg")

    image_path = media_root / pin.image
    if not image_path.exists():
        return FileResponse(default_image, media_type="image/jpeg")

    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    return FileResponse(image_path, media_type=mime_type)



@router.get("/search/tags-with-first-pin", response_model=list[dict])
async def get_tags_with_first_pin(user_id: user_id, db: db):
    result = []

    tags_stmt = select(TagsOrm).limit(8)
    tags_result = await db.execute(tags_stmt)
    tags = tags_result.scalars().all()

    for tag in tags:
        stmt = (
            select(PinsOrm)
            .join(pins_tags, PinsOrm.id == pins_tags.c.pin_id)
            .where(pins_tags.c.tag_id == tag.id)
            .limit(1)
        )
        pin_result = await db.execute(stmt)
        pin = pin_result.scalar_one_or_none()

        if pin:
            result.append({"id": tag.id, "name": tag.name, "pinId": pin.id})

    return result


RELATED_PAGE_MAX = 40
RELATED_ASSEMBLE_CAP = 200
RELATED_TAG_CAP = 150
RELATED_COSAVE_CAP = 40
RELATED_AUTHOR_ANY_CAP = 4
RELATED_RANDOM_CAP = 8


def _wilson_lower(likes: int, views: int) -> float:
    """Lower bound of like/view. Zero views stay at the bottom (no division by zero)."""
    n = int(views or 0)
    if n <= 0:
        return 0.0
    ph = min(1.0, max(0.0, int(likes or 0) / n))
    z = 1.96
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = ph + z2 / (2.0 * n)
    margin = z * math.sqrt((ph * (1.0 - ph) + z2 / (4.0 * n)) / n)
    return max(0.0, (centre - margin) / denom)


@router.get("/{pin_id}", response_model=list[PinOut])
async def get_related_pins(db: db, user_id: user_id, pin_id: int, filter: filter):
    """Related pins for pin detail, paginated.

    Fill order:
      1) tag overlap, ranked by Jaccard × Wilson lower bound
      2) limited co-save (same boards)
      3) same author, any tags, hard cap
      4) a small random fill
    """
    _ = user_id
    page_limit = max(1, min(int(filter.limit or 20), RELATED_PAGE_MAX))
    page_offset = max(0, int(filter.offset or 0))
    assemble_target = min(page_offset + page_limit, RELATED_ASSEMBLE_CAP)

    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    tag_rows = await db.execute(select(pins_tags.c.tag_id).where(pins_tags.c.pin_id == pin_id))
    tag_ids = [int(row[0]) for row in tag_rows.all()]

    picked: list[int] = []
    if tag_ids:
        overlap_rows = await db.execute(
            select(pins_tags.c.pin_id, func.count())
            .where(pins_tags.c.tag_id.in_(tag_ids), pins_tags.c.pin_id != pin_id)
            .group_by(pins_tags.c.pin_id)
            .order_by(desc(func.count()))
            .limit(RELATED_TAG_CAP)
        )
        overlap_counts = {int(pid): int(cnt) for pid, cnt in overlap_rows.all()}
        ids = list(overlap_counts)
        tag_counts: dict[int, int] = {}
        likes_map: dict[int, int] = {}
        views_map: dict[int, int] = {}
        if ids:
            tag_count_rows = await db.execute(
                select(pins_tags.c.pin_id, func.count())
                .where(pins_tags.c.pin_id.in_(ids))
                .group_by(pins_tags.c.pin_id)
            )
            tag_counts = {int(pid): int(cnt) for pid, cnt in tag_count_rows.all()}
            like_rows = await db.execute(
                select(LikesOrm.pin_id, func.count())
                .where(LikesOrm.pin_id.in_(ids))
                .group_by(LikesOrm.pin_id)
            )
            likes_map = {int(pid): int(cnt) for pid, cnt in like_rows.all() if pid is not None}
            view_rows = await db.execute(
                select(PinStatsOrm.pin_id, PinStatsOrm.view_count).where(PinStatsOrm.pin_id.in_(ids))
            )
            views_map = {int(pid): int(views or 0) for pid, views in view_rows.all()}
        na = len(tag_ids)
        ranked: list[tuple[float, int]] = []
        for other_id, overlap in overlap_counts.items():
            nb = tag_counts.get(other_id, overlap)
            denom = na + nb - overlap
            jaccard = (overlap / denom) if denom > 0 else 0.0
            wilson = _wilson_lower(likes_map.get(other_id, 0), views_map.get(other_id, 0))
            ranked.append((jaccard * (0.15 + wilson), other_id))
        ranked.sort(key=lambda item: (-item[0], -item[1]))
        picked = [other_id for _, other_id in ranked]

    have = set(picked)
    if len(picked) < assemble_target:
        boards = select(board_pins.c.board_id).where(board_pins.c.pin_id == pin_id)
        cosave_rows = await db.execute(
            select(board_pins.c.pin_id, func.count())
            .where(board_pins.c.board_id.in_(boards), board_pins.c.pin_id != pin_id)
            .group_by(board_pins.c.pin_id)
            .order_by(desc(func.count()))
            .limit(RELATED_COSAVE_CAP)
        )
        for other_id, _cnt in cosave_rows.all():
            other_id = int(other_id)
            if other_id in have or other_id == pin_id:
                continue
            picked.append(other_id)
            have.add(other_id)
            if len(picked) >= assemble_target:
                break

    author_added = 0
    if len(picked) < assemble_target:
        author_rows = await db.scalars(
            select(PinsOrm.id)
            .where(PinsOrm.user_id == pin.user_id, PinsOrm.id != pin_id)
            .order_by(desc(PinsOrm.id))
            .limit(RELATED_AUTHOR_ANY_CAP + len(picked))
        )
        for other_id in author_rows.all():
            other_id = int(other_id)
            if other_id in have:
                continue
            picked.append(other_id)
            have.add(other_id)
            author_added += 1
            if author_added >= RELATED_AUTHOR_ANY_CAP or len(picked) >= assemble_target:
                break

    if len(picked) < assemble_target:
        need = min(RELATED_RANDOM_CAP, assemble_target - len(picked))
        random_stmt = select(PinsOrm.id).where(PinsOrm.id != pin_id)
        if picked:
            random_stmt = random_stmt.where(PinsOrm.id.notin_(picked))
        random_stmt = random_stmt.order_by(func.random()).limit(need)
        for other_id in (await db.scalars(random_stmt)).all():
            picked.append(int(other_id))

    page_ids = picked[page_offset : page_offset + page_limit]
    if not page_ids:
        return []
    rows = list((await db.scalars(select(PinsOrm).where(PinsOrm.id.in_(page_ids)))).all())
    by_id = {row.id: row for row in rows}
    ordered = [by_id[pid] for pid in page_ids if pid in by_id]
    return await pins_out(db, ordered)


@router.get("/pin/tags/{pin_id}", response_model=list[TagOut])
async def get_tags_on_pin(db: db, user_id: user_id, pin_id: int):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    result = await db.execute(select(pins_tags).where(pins_tags.c.pin_id == pin_id))
    rows = result.all()

    tags = []

    for row in rows:
        tag_id = row[1]
        tag = await db.scalar(select(TagsOrm).where(TagsOrm.id == tag_id))
        tags.append(tag)
    return tags
