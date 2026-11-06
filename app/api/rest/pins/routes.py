import json
import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from datetime import datetime, timezone

from sqlalchemy import delete, desc, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.rest.dependencies import db, filter, filter_with_value, optional_user_id, user_id
from app.api.rest.ownership import assert_can_access_pin_original, assert_pin_owner
from app.api.rest.role_gates import assert_can_create_pin
from app.api.rest.pins.media_signing import (
    build_original_file_path,
    verify_original_signature,
)
from app.api.rest.pins.watermark import original_dir
from app.api.rest.utils import save_file
from app.config import settings
from app.postgresql.models import (
    BoardsOrm,
    CommentsOrm,
    LikesOrm,
    PinAiAnalysesOrm,
    PinImagesOrm,
    PinOriginalAccessLogsOrm,
    PinStatsOrm,
    PinsOrm,
    TagsOrm,
    UsersOrm,
    board_pins,
    pins_tags,
    users_pins,
)

from .feed_meta import build_feed_meta, meta_by_pin_id
from .pin_out import pin_out as _pin_out
from .pin_out import pins_out as _pins_out
from .schemas import (
    FeedMetaIn,
    FeedMetaOut,
    KeywordSuggestOut,
    OriginalUrlOut,
    PinAiAnalysisOut,
    PinEngagementOut,
    PinIn,
    PinOut,
)
from .search_service import (
    list_pins_for_target,
    resolve_search_target,
    suggest_keywords,
)

mimetypes.add_type("image/webp", ".webp")

from app.ai.tasks import analyze_pin_image
from app.celery.tasks import (
    generate_pin_preview,
    make_update_pin_created_for_followers,
    make_update_save_pin,
    user_view_pin,
)

router = APIRouter(prefix="/pins", tags=["pins"])


async def _enqueue_auto_tag(db, pin_id: int) -> None:
    """Mark pending + push Celery fair queue (no-op when feature flag off)."""
    if not settings.AI_AUTO_TAG_ENABLED:
        return
    now = datetime.now(timezone.utc)
    await db.execute(
        pg_insert(PinAiAnalysesOrm)
        .values(
            pin_id=pin_id,
            status="pending",
            error_message=None,
            suggested_tags=None,
            incorrect_tags=None,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=["pin_id"],
            set_={
                "status": "pending",
                "error_message": None,
                "suggested_tags": None,
                "incorrect_tags": None,
                "updated_at": now,
            },
        )
    )
    await db.commit()
    analyze_pin_image.delay(pin_id)

MAX_PIN_IMAGES = 50

ALLOWED_FILE_TYPES = [
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "image/webp",
    "image/png",
    "image/bmp",
    "video/mp4",
    "video/webm",
]


def _unlink_media_rel(rel: str | None) -> None:
    if not rel:
        return
    path = Path(settings.MEDIA_PATH) / rel
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, (ua[:400] if ua else None)


async def _log_original_access(
    db_session,
    *,
    pin_id: int,
    access_user_id: int,
    action: str,
    request: Request,
) -> None:
    ip, ua = _client_meta(request)
    await db_session.execute(
        insert(PinOriginalAccessLogsOrm).values(
            pin_id=pin_id,
            user_id=access_user_id,
            action=action,
            ip=ip,
            user_agent=ua,
        )
    )


def _default_preview_file() -> Path:
    return Path(settings.MEDIA_PATH) / "notauth" / "1.jpg"


@router.get("/", response_model=list[PinOut])
async def get_pins(
    db: db,
    filter: filter,
    user_id: optional_user_id,
    mode: str = Query("home"),
):
    """Home feed: `mode=home` reorders chrono universe; `mode=chrono` newest-first.

    Guest (no auth): popularity like > view > comment > save.
    Logged-in: affinity / following personalization.
    Ranking never gates the grid — any failure or thin page falls back to chrono.
    """
    from app.api.rest.pins.feed_ranker import build_home_feed_pin_ids, pins_chrono

    feed_mode = mode if mode in ("home", "chrono") else "home"

    try:
        if feed_mode == "chrono":
            pins = await pins_chrono(db, offset=filter.offset, limit=filter.limit)
            return await _pins_out(db, pins)

        pin_ids = await build_home_feed_pin_ids(
            db,
            user_id=user_id,
            offset=filter.offset,
            limit=filter.limit,
        )
        by_id = {
            p.id: p
            for p in (
                await db.scalars(select(PinsOrm).where(PinsOrm.id.in_(pin_ids)))
            ).all()
        } if pin_ids else {}
        ordered = [by_id[pid] for pid in pin_ids if pid in by_id]

        # Pad / replace with chrono so personalization never blanks the feed
        if len(ordered) < filter.limit:
            chrono = await pins_chrono(
                db, offset=filter.offset, limit=filter.limit
            )
            if not ordered:
                return await _pins_out(db, chrono)
            seen = {p.id for p in ordered}
            for p in chrono:
                if p.id in seen:
                    continue
                ordered.append(p)
                if len(ordered) >= filter.limit:
                    break
        return await _pins_out(db, ordered)
    except Exception as e:
        # AC-24: never 500 the home grid — fall back to timeline
        from app.logger import logger

        logger.error(f"home feed ranker failed, chrono fallback: {e}", exc_info=True)
        pins = await pins_chrono(db, offset=filter.offset, limit=filter.limit)
        return await _pins_out(db, pins)


@router.post("/feed-meta", response_model=list[FeedMetaOut])
async def get_feed_meta(
    body: FeedMetaIn, db: db, user_id: optional_user_id, response: Response
):
    """Batch username + like/comment counts for feed cards (cuts N+1)."""
    # Includes per-user `liked` — never shared-cache.
    response.headers["Cache-Control"] = "private, no-store"
    return await build_feed_meta(db, body.pin_ids or [], user_id=user_id)


@router.get("/tag/{tag_name}", response_model=list[PinOut])
async def get_pins_by_tag(tag_name: str, user_id: user_id, db: db, filter: filter):
    tag = await db.scalar(select(TagsOrm).where(TagsOrm.name == tag_name))
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tag not found")

    result = await db.execute(select(pins_tags).where(pins_tags.c.tag_id == tag.id))
    rows = result.all()
    pins = []
    for row in rows:
        pin_id = row[0]
        pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
        pins.append(pin)
    sliced = pins[filter.offset : filter.offset + filter.limit]
    return await _pins_out(db, sliced)


@router.get("/suggest-keywords", response_model=list[KeywordSuggestOut])
async def suggest_pin_keywords(
    user_id: user_id,
    db: db,
    q: str = Query("", max_length=100),
    limit: int = Query(10, ge=1, le=20),
):
    """L1 realtime: tag/author vocabulary only — never scans pins."""
    rows = await suggest_keywords(
        db, q=q, limit=limit, exclude_user_id=user_id
    )
    return [KeywordSuggestOut(**r) for r in rows]


@router.get("/search", response_model=list[PinOut])
async def search_pins(
    filter_with_value: filter_with_value,
    user_id: user_id,
    db: db,
    response: Response,
    tag_id: int | None = Query(None, ge=1),
    author_id: int | None = Query(None, ge=1),
):
    """
    Enter-only pin search: free-text resolves ranked tags (exact→prefix→contains)
    or exact author. Embeds feed-meta per-request (liked never Redis-cached with ids).
    """
    # Embeds per-user `liked` — forbid shared HTTP caches.
    response.headers["Cache-Control"] = "private, no-store"
    target = await resolve_search_target(
        db,
        value=filter_with_value.value,
        tag_id=tag_id,
        author_id=author_id,
    )
    if target.get("kind") == "none":
        return []
    pins = await list_pins_for_target(
        db,
        target=target,
        offset=filter_with_value.offset,
        limit=filter_with_value.limit,
    )
    meta_map = meta_by_pin_id(
        await build_feed_meta(db, [p.id for p in pins], user_id=user_id)
    )
    for pin in pins:
        row = meta_map.get(pin.id)
        if row is None:
            continue
        pin._feed_meta_out = {
            "username": row.username,
            "likes_count": row.likes_count,
            "liked": row.liked,
            "comments_count": row.comments_count,
        }
    return await _pins_out(db, pins)


@router.post("/", response_model=PinOut, status_code=status.HTTP_201_CREATED)
async def create_pin(user_id: user_id, db: db, pin_model: PinIn):
    await assert_can_create_pin(db, user_id)
    pin = await db.scalar(
        insert(PinsOrm).values(**pin_model.model_dump(), user_id=user_id).returning(PinsOrm)
    )
    await db.execute(insert(PinStatsOrm).values(pin_id=pin.id, view_count=0))
    await db.commit()
    return await _pin_out(db, pin)


@router.post("/create-pin-entity", response_model=PinOut, status_code=status.HTTP_201_CREATED)
async def create_pin_entity(
    user_id: user_id,
    db: db,
    pin_model: str = Form(...),
    files: list[UploadFile] | None = File(None),
    file: UploadFile | None = File(None),
):
    await assert_can_create_pin(db, user_id)

    uploads: list[UploadFile] = list(files) if files else []
    if not uploads and file is not None:
        uploads = [file]
    if not uploads:
        raise HTTPException(status_code=422, detail="at_least_one_file_required")
    if len(uploads) > MAX_PIN_IMAGES:
        raise HTTPException(
            status_code=422,
            detail=f"max_{MAX_PIN_IMAGES}_images_per_collection",
        )

    for upload in uploads:
        if upload.content_type not in ALLOWED_FILE_TYPES:
            raise HTTPException(status_code=415, detail="Invalid file type")

    pin_data = json.loads(pin_model)
    pin = await db.scalar(
        insert(PinsOrm).values(**pin_data, user_id=user_id).returning(PinsOrm)
    )
    await db.execute(insert(PinStatsOrm).values(pin_id=pin.id, view_count=0))

    original_rels: list[str] = []
    for upload in uploads:
        filename = f"{uuid.uuid4()}{Path(upload.filename or 'upload.bin').suffix}"
        full_path = original_dir() / filename
        await save_file(upload, str(full_path))
        original_rels.append(f"pins/original/{filename}")

    for sort_order, original_rel in enumerate(original_rels):
        await db.execute(
            insert(PinImagesOrm).values(
                pin_id=pin.id,
                original_image=original_rel,
                sort_order=sort_order,
            )
        )

    pin = await db.scalar(
        update(PinsOrm)
        .where(PinsOrm.id == pin.id)
        .values(original_image=original_rels[0])
        .returning(PinsOrm)
    )
    await db.commit()

    pin_id = pin.id
    generate_pin_preview.run(pin_id)
    await _enqueue_auto_tag(db, pin_id)
    db.expire_all()
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    make_update_pin_created_for_followers.delay(user_id, pin.id)
    return await _pin_out(db, pin)


@router.delete("/{pin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def user_delete_created_pin(pin_id: int, user_id: user_id, db: db):
    await assert_pin_owner(db, pin_id, user_id)
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    image_rows = (
        await db.scalars(select(PinImagesOrm).where(PinImagesOrm.pin_id == pin_id))
    ).all()
    for row in image_rows:
        _unlink_media_rel(row.image)
        _unlink_media_rel(row.original_image)
    if pin is not None:
        _unlink_media_rel(pin.image)
        _unlink_media_rel(pin.videoPreview)
        _unlink_media_rel(pin.original_image)
    await db.execute(delete(PinsOrm).where(PinsOrm.id == pin_id))
    await db.commit()
    return {"status", "ok"}


@router.post("/upload/{id}", response_model=PinOut)
async def upload_image(user_id: user_id, id: int, db: db, file: UploadFile):
    await assert_pin_owner(db, id, user_id)

    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=415, detail="Invalid file type")

    filename = f"{uuid.uuid4()}{Path(file.filename or 'upload.bin').suffix}"
    full_path = original_dir() / filename
    await save_file(file, str(full_path))
    original_rel = f"pins/original/{filename}"

    # Replace collection with a single image (legacy replace-upload)
    old_rows = (
        await db.scalars(select(PinImagesOrm).where(PinImagesOrm.pin_id == id))
    ).all()
    for row in old_rows:
        _unlink_media_rel(row.image)
        _unlink_media_rel(row.original_image)
    await db.execute(delete(PinImagesOrm).where(PinImagesOrm.pin_id == id))
    await db.execute(
        insert(PinImagesOrm).values(
            pin_id=id,
            original_image=original_rel,
            sort_order=0,
        )
    )

    pin = await db.scalar(
        update(PinsOrm)
        .where(PinsOrm.id == id)
        .values(original_image=original_rel, image=None, videoPreview=None)
        .returning(PinsOrm)
    )
    await db.commit()

    pin_id = pin.id
    generate_pin_preview.run(pin_id)
    await _enqueue_auto_tag(db, pin_id)
    db.expire_all()
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    return await _pin_out(db, pin)


@router.get("/upload/{id}")
async def get_image(
    id: int,
    db: db,
    user_id: optional_user_id,
    image_id: int | None = Query(None),
):
    """Serve watermarked preview only — never the original. Anonymous OK for feed."""
    _ = user_id
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == id))
    if pin is None:
        raise HTTPException(status_code=404, detail="pin not found")

    media_root = Path(settings.MEDIA_PATH)
    default_image = _default_preview_file()

    preview_rel = None
    if image_id is not None:
        row = await db.scalar(
            select(PinImagesOrm).where(
                PinImagesOrm.id == image_id,
                PinImagesOrm.pin_id == id,
            )
        )
        if row is None:
            raise HTTPException(status_code=404, detail="pin_image_not_found")
        preview_rel = row.image
        if not preview_rel and row.sort_order == 0:
            preview_rel = pin.image or pin.videoPreview
    else:
        preview_rel = pin.image or pin.videoPreview

    # URL is pin-id based (content can change on re-preview) — cache briefly,
    # never `immutable`, so ETag/Last-Modified can still refresh after edits.
    cache_headers = {"Cache-Control": "public, max-age=3600"}

    if not preview_rel:
        return FileResponse(
            default_image,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=60"},
        )

    full_path = media_root / preview_rel
    if not full_path.exists():
        return FileResponse(
            default_image,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=60"},
        )

    mime_type, _ = mimetypes.guess_type(str(full_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    return FileResponse(full_path, media_type=mime_type, headers=cache_headers)


@router.get("/original/{id}", response_model=OriginalUrlOut)
async def get_original_signed_url(request: Request, user_id: user_id, id: int, db: db):
    pin = await assert_can_access_pin_original(db, id, user_id)
    if not pin.original_image:
        raise HTTPException(status_code=404, detail="original_not_found")

    await _log_original_access(
        db, pin_id=id, access_user_id=user_id, action="mint", request=request
    )
    await db.commit()

    url = build_original_file_path(id, user_id)
    return OriginalUrlOut(url=url, expires_in=settings.PIN_ORIGINAL_URL_TTL_SECONDS)


@router.get("/original/{id}/file")
async def get_original_file(
    request: Request,
    id: int,
    exp: int = Query(...),
    uid: int = Query(...),
    sig: str = Query(...),
):
    verify_original_signature(id, uid, exp, sig)

    from app.api.rest.ownership import assert_can_access_pin_original
    from app.postgresql.database import async_session_maker

    async with async_session_maker() as session:
        # Re-check ACL even if signed URL was leaked within TTL.
        pin = await assert_can_access_pin_original(session, id, uid)
        if not pin.original_image:
            raise HTTPException(status_code=404, detail="original_not_found")
        full_path = Path(settings.MEDIA_PATH) / pin.original_image
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="original_file_missing")

        await _log_original_access(
            session, pin_id=id, access_user_id=uid, action="file", request=request
        )
        await session.commit()

        mime_type, _ = mimetypes.guess_type(str(full_path))
        if mime_type is None:
            mime_type = "application/octet-stream"
        return FileResponse(full_path, media_type=mime_type)


@router.get("/{id}", response_model=PinOut)
async def get_pin_by_id(user_id: user_id, id: int, db: db):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    user_view_pin.delay(user_id, id)

    return await _pin_out(db, pin)


@router.get("/{id}/ai-analysis", response_model=PinAiAnalysisOut)
async def get_pin_ai_analysis(id: int, user_id: user_id, db: db):
    """Owner-only poll for Gemini auto-tag status."""
    await assert_pin_owner(db, id, user_id)
    row = await db.get(PinAiAnalysesOrm, id)
    if row is None:
        return PinAiAnalysisOut(pin_id=id, status="none")
    tags = row.suggested_tags if isinstance(row.suggested_tags, list) else []
    incorrect = row.incorrect_tags if isinstance(row.incorrect_tags, list) else []
    return PinAiAnalysisOut(
        pin_id=id,
        status=row.status,
        suggested_tags=[str(t) for t in tags],
        incorrect_tags=[str(t) for t in incorrect],
        error_message=row.error_message,
        updated_at=row.updated_at,
    )


@router.get("/{id}/engagement", response_model=PinEngagementOut)
async def get_pin_engagement(id: int, user_id: user_id, db: db):
    """Likes + unique savers + unique detail viewers (users_view_pins → pin_stats.view_count)."""
    _ = user_id
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    likes_count = int(
        await db.scalar(
            select(func.count()).select_from(LikesOrm).where(LikesOrm.pin_id == id)
        )
        or 0
    )

    profile_savers = select(users_pins.c.user_id.label("uid")).where(users_pins.c.pin_id == id)
    board_savers = (
        select(BoardsOrm.user_id.label("uid"))
        .join(board_pins, board_pins.c.board_id == BoardsOrm.id)
        .where(board_pins.c.pin_id == id)
    )
    savers = profile_savers.union(board_savers).subquery()
    saves_count = int(
        await db.scalar(select(func.count()).select_from(savers)) or 0
    )

    views_count = int(
        await db.scalar(
            select(PinStatsOrm.view_count).where(PinStatsOrm.pin_id == id)
        )
        or 0
    )

    return PinEngagementOut(
        pin_id=id,
        likes_count=likes_count,
        saves_count=saves_count,
        views_count=views_count,
    )


@router.get("/user_created_pins/{id}", response_model=list[PinOut])
async def get_user_created_pins(id: int, user_id: user_id, db: db, filter: filter):
    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    pins = await db.scalars(
        select(PinsOrm)
        .where(PinsOrm.user_id == id)
        .offset(filter.offset)
        .limit(filter.limit)
        .order_by(desc(PinsOrm.id))
    )
    return await _pins_out(db, pins)


@router.post("/user_saved_pins/{pin_id}", status_code=status.HTTP_201_CREATED)
async def user_save_pin(pin_id: int, user_id: user_id, db: db):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    query = select(users_pins).where(users_pins.c.user_id == user_id, users_pins.c.pin_id == pin_id)
    result = await db.execute(query)
    user_pin = result.fetchone()

    if user_pin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already saved this pin"
        )

    await db.execute(insert(users_pins).values(user_id=user_id, pin_id=pin_id))
    await db.commit()

    if pin.user_id != user_id:
        make_update_save_pin.delay(pin.user_id, user_id, pin_id, "Profile")

    return {"status", "ok"}


@router.delete("/user_saved_pins/{pin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def user_delete_saved_pin(pin_id: int, user_id: user_id, db: db):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    await db.execute(
        delete(users_pins).where(users_pins.c.user_id == user_id, users_pins.c.pin_id == pin_id)
    )
    await db.commit()
    return {"status", "ok"}


@router.get("/user_saved_pins/{id}", response_model=list[PinOut])
async def get_user_saved_pins(id: int, user_id: user_id, db: db, filter: filter):
    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    result = await db.execute(
        select(users_pins)
        .where(users_pins.c.user_id == id)
        .order_by(users_pins.c.created_at.desc(), users_pins.c.pin_id.desc())
        .offset(filter.offset)
        .limit(filter.limit)
    )
    rows = result.all()
    pins = []
    for row in rows:
        pin_id = row[1]
        pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
        if pin is not None:
            pins.append(pin)
    return await _pins_out(db, pins)


@router.get("/user_liked_pins/{id}", response_model=list[PinOut])
async def get_user_liked_pins(id: int, user_id: user_id, db: db, filter: filter):
    user = await db.scalar(select(UsersOrm).where(UsersOrm.id == id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    result = await db.execute(
        select(PinsOrm)
        .join(LikesOrm, PinsOrm.id == LikesOrm.pin_id)
        .where(LikesOrm.user_id == id)
        .offset(filter.offset)
        .limit(filter.limit)
    )
    pins = result.scalars().all()

    return await _pins_out(db, pins)
