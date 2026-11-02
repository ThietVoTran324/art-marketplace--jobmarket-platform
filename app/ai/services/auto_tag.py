"""Normalize Gemini tags and merge onto a pin without removing user tags."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ai.providers.gemini import suggest_tags_for_image
from app.ai.schemas import ImageTagResult
from app.api.rest.pins.watermark import media_root
from app.api.rest.text_normalize import fold_search_text
from app.config import settings
from app.logger import logger
from app.postgresql.models import PinAiAnalysesOrm, PinImagesOrm, PinsOrm, TagsOrm, pins_tags

# Keep kebab-case from the model (oil-on-canvas); drop other punctuation.
_TAG_TOKEN_RE = re.compile(r"[^a-z0-9\-]+")


def normalize_tag_name(raw: str) -> str:
    """Strip #, fold accents/case, keep lowercase kebab-case tokens."""
    text = raw.strip().lstrip("#").replace("_", "-").replace(" ", "-")
    folded = fold_search_text(text)
    token = _TAG_TOKEN_RE.sub("-", folded)
    token = re.sub(r"-{2,}", "-", token).strip("-")
    if token in {"unknown", "n-a", "na", "none", "null"}:
        return ""
    return token[:100]


def normalize_many(result: ImageTagResult, *, max_tags: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in result.tags:
        name = normalize_tag_name(item.name)
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
        if len(out) >= max_tags:
            break
    return out


def _resolve_original_path(db: Session, pin: PinsOrm) -> Path | None:
    img_row = db.scalar(
        select(PinImagesOrm)
        .where(PinImagesOrm.pin_id == pin.id)
        .order_by(PinImagesOrm.sort_order.asc(), PinImagesOrm.id.asc())
        .limit(1)
    )
    rel = None
    if img_row is not None and img_row.original_image:
        rel = img_row.original_image
    elif pin.original_image:
        rel = pin.original_image
    if not rel:
        return None
    path = media_root() / rel
    return path if path.is_file() else None


def upsert_analysis(
    db: Session,
    pin_id: int,
    *,
    status: str,
    error_message: str | None = None,
    tags: list[str] | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    payload = {
        "pin_id": pin_id,
        "status": status,
        "error_message": error_message,
        "suggested_tags": tags,
        "updated_at": now,
    }
    stmt = (
        pg_insert(PinAiAnalysesOrm)
        .values(**payload, created_at=now)
        .on_conflict_do_update(
            index_elements=["pin_id"],
            set_={
                "status": status,
                "error_message": error_message,
                "suggested_tags": tags,
                "updated_at": now,
            },
        )
    )
    db.execute(stmt)


def _get_or_create_tag(db: Session, name: str) -> TagsOrm:
    existing = db.scalar(select(TagsOrm).where(TagsOrm.name == name))
    if existing is not None:
        return existing
    inserted = db.scalar(
        pg_insert(TagsOrm)
        .values(name=name)
        .on_conflict_do_nothing(index_elements=["name"])
        .returning(TagsOrm)
    )
    if inserted is not None:
        return inserted
    again = db.scalar(select(TagsOrm).where(TagsOrm.name == name))
    if again is None:
        raise RuntimeError(f"failed to get_or_create tag name={name}")
    return again


def _link_pin_tag(db: Session, pin_id: int, tag_id: int) -> None:
    db.execute(
        pg_insert(pins_tags)
        .values(pin_id=pin_id, tag_id=tag_id)
        .on_conflict_do_nothing(index_elements=["pin_id", "tag_id"])
    )


def run_auto_tag(db: Session, pin_id: int) -> dict:
    """Full auto-tag pipeline for one pin. Caller owns commit/rollback."""
    pin = db.get(PinsOrm, pin_id)
    if pin is None:
        upsert_analysis(db, pin_id, status="skipped", error_message="no_pin")
        return {"status": "skipped", "reason": "no_pin"}

    path = _resolve_original_path(db, pin)
    if path is None:
        upsert_analysis(db, pin_id, status="skipped", error_message="missing_file")
        return {"status": "skipped", "reason": "missing_file"}

    if path.suffix.lower() in {".mp4", ".webm", ".mov"}:
        upsert_analysis(db, pin_id, status="skipped", error_message="not_an_image")
        return {"status": "skipped", "reason": "not_an_image"}

    upsert_analysis(db, pin_id, status="running")
    db.flush()

    result = suggest_tags_for_image(path)
    names = normalize_many(result, max_tags=settings.AI_AUTO_TAG_MAX_TAGS)
    linked: list[str] = []
    for name in names:
        tag = _get_or_create_tag(db, name)
        _link_pin_tag(db, pin_id, tag.id)
        linked.append(name)
    upsert_analysis(db, pin_id, status="done", tags=linked)
    logger.info("auto-tag done pin_id=%s tags=%s", pin_id, linked)
    return {"status": "done", "tags": linked}
