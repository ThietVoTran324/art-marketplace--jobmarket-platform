"""Offline reindex: FAQ md, pin parent–child, tag catalog embeddings.

Throttling mirrors scripts/backfill_pin_ai_tags (limit + per-request/batch pauses)
so Gemini quota stops the run cleanly instead of failing mid-flight.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.rag.chunking import chunk_markdown, content_sha256
from app.ai.rag.embed import embed_texts
from app.ai.rag.pin_chunks import build_pin_child_chunks, pin_document_hash
from app.config import settings
from app.logger import logger
from app.postgresql.models import (
    AiRagChunksOrm,
    AiRagDocumentsOrm,
    AiRagTagEmbeddingsOrm,
    PinsOrm,
    TagsOrm,
    pins_tags,
)

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"


class ReindexRateLimited(Exception):
    """Raised when embed provider returns 429 / quota; caller should stop gracefully."""

    def __init__(self, message: str, *, stats: dict[str, Any]):
        super().__init__(message)
        self.stats = stats


def _is_rate_limit_error(exc: BaseException) -> bool:
    current: BaseException | None = exc
    keywords = (
        "resource_exhausted",
        "too many requests",
        "rate limit",
        "quota exceeded",
        "429",
    )
    while current is not None:
        status = getattr(current, "status_code", None)
        code = getattr(current, "code", None)
        if status == 429 or code == 429 or code == "429":
            return True
        name = type(current).__name__.lower()
        if "resource_exhausted" in name:
            return True
        message = str(current).lower()
        if any(k in message for k in keywords):
            return True
        current = current.__cause__ or current.__context__
    return False


def corpus_dir() -> Path:
    return CORPUS_DIR


def list_faq_files(directory: Path | None = None) -> list[Path]:
    root = directory or CORPUS_DIR
    if not root.is_dir():
        return []
    return sorted(p for p in root.glob("*.md") if p.is_file())


def _title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip() or fallback
    return fallback


def _default_request_pause_sec(explicit: float | None) -> float:
    if explicit is not None:
        return max(0.0, float(explicit))
    rpm = int(settings.AI_RAG_EMBED_RPM or 0)
    if rpm > 0:
        return max(0.0, 60.0 / float(rpm))
    return float(settings.AI_RAG_REINDEX_REQUEST_PAUSE_SEC or 0.0)


def _throttle_params(
    *,
    limit: int | None,
    batch_size: int | None,
    batch_pause_sec: float | None,
    request_pause_sec: float | None,
) -> dict[str, Any]:
    return {
        "limit": max(
            1,
            int(
                limit
                if limit is not None
                else settings.AI_RAG_REINDEX_LIMIT or 250
            ),
        ),
        "batch_size": max(
            1,
            int(
                batch_size
                if batch_size is not None
                else settings.AI_RAG_REINDEX_BATCH_SIZE or 15
            ),
        ),
        "batch_pause_sec": max(
            0.0,
            float(
                batch_pause_sec
                if batch_pause_sec is not None
                else settings.AI_RAG_REINDEX_BATCH_PAUSE_SEC or 0.0
            ),
        ),
        "request_pause_sec": _default_request_pause_sec(request_pause_sec),
    }


def _pause_between(
    *,
    index: int,
    total: int,
    batch_size: int,
    batch_pause_sec: float,
    request_pause_sec: float,
) -> None:
    """Sleep after a unit of work (not after the last item)."""
    if index + 1 >= total:
        return
    if request_pause_sec > 0:
        time.sleep(request_pause_sec)
    if (index + 1) % batch_size == 0 and batch_pause_sec > 0:
        logger.info("rag reindex pause %.1fs before next batch", batch_pause_sec)
        time.sleep(batch_pause_sec)


def _embed_or_rate_limit(
    texts: list[str],
    *,
    task_type: str,
    stats: dict[str, Any],
) -> list[list[float]]:
    try:
        return embed_texts(texts, task_type=task_type)
    except Exception as exc:  # noqa: BLE001 — classify 429 then re-raise others
        if _is_rate_limit_error(exc):
            stats["stopped_reason"] = "rate_limit"
            raise ReindexRateLimited(str(exc), stats=stats) from exc
        raise


def reindex_faq_corpus(
    db: Session,
    *,
    directory: Path | None = None,
    dry_run: bool = False,
    limit: int | None = None,
    batch_size: int | None = None,
    batch_pause_sec: float | None = None,
    request_pause_sec: float | None = None,
) -> dict[str, Any]:
    if not settings.AI_RAG_ENABLED and not dry_run:
        logger.warning("AI_RAG_ENABLED=false — reindex still runs when invoked explicitly")

    throttle = _throttle_params(
        limit=limit,
        batch_size=batch_size,
        batch_pause_sec=batch_pause_sec,
        request_pause_sec=request_pause_sec,
    )
    all_files = list_faq_files(directory)
    files = all_files[: throttle["limit"]]
    stats: dict[str, Any] = {
        "files": len(files),
        "upserted": 0,
        "skipped": 0,
        "chunks": 0,
        "deleted_stale": 0,
        "dry_run": dry_run,
        "limit": throttle["limit"],
        "batch_size": throttle["batch_size"],
        "stopped_reason": None,
    }
    seen_keys: set[str] = set()

    for i, path in enumerate(files):
        source_key = path.stem
        seen_keys.add(source_key)
        raw = path.read_text(encoding="utf-8")
        doc_hash = content_sha256(raw)
        title = _title_from_markdown(raw, source_key)
        rel_path = f"app/ai/rag/corpus/{path.name}"

        existing = db.scalar(
            select(AiRagDocumentsOrm).where(
                AiRagDocumentsOrm.source_type == "faq",
                AiRagDocumentsOrm.source_key == source_key,
            )
        )
        if existing is not None and existing.content_hash == doc_hash:
            stats["skipped"] += 1
            _pause_between(
                index=i,
                total=len(files),
                batch_size=throttle["batch_size"],
                batch_pause_sec=throttle["batch_pause_sec"],
                request_pause_sec=0.0,  # no embed call
            )
            continue

        chunks = chunk_markdown(raw)
        if dry_run:
            stats["upserted"] += 1
            stats["chunks"] += len(chunks)
            continue

        if existing is None:
            existing = AiRagDocumentsOrm(
                source_type="faq",
                source_key=source_key,
                title=title,
                path=rel_path,
                body=raw,
                content_hash=doc_hash,
                meta={"corpus_file": path.name},
            )
            db.add(existing)
            db.flush()
        else:
            existing.title = title
            existing.path = rel_path
            existing.body = raw
            existing.content_hash = doc_hash
            existing.meta = {**(existing.meta or {}), "corpus_file": path.name}
            existing.updated_at = datetime.now(timezone.utc)
            db.execute(
                delete(AiRagChunksOrm).where(AiRagChunksOrm.document_id == existing.id)
            )
            db.flush()

        embeddings = _embed_or_rate_limit(
            [c.content for c in chunks],
            task_type="retrieval_document",
            stats=stats,
        )
        for ch, vec in zip(chunks, embeddings, strict=True):
            db.add(
                AiRagChunksOrm(
                    document_id=existing.id,
                    chunk_index=ch.chunk_index,
                    chunk_kind="faq_section",
                    heading=ch.heading,
                    content=ch.content,
                    content_hash=ch.content_hash,
                    embedding=vec,
                    meta={},
                )
            )
        stats["upserted"] += 1
        stats["chunks"] += len(chunks)
        db.commit()
        logger.info("rag reindex faq=%s chunks=%s", source_key, len(chunks))
        _pause_between(
            index=i,
            total=len(files),
            batch_size=throttle["batch_size"],
            batch_pause_sec=throttle["batch_pause_sec"],
            request_pause_sec=throttle["request_pause_sec"],
        )

    # Only prune stale FAQ docs when this run covered the full corpus.
    if (
        not dry_run
        and stats.get("stopped_reason") is None
        and len(files) == len(all_files)
    ):
        stale = (
            db.scalars(
                select(AiRagDocumentsOrm).where(AiRagDocumentsOrm.source_type == "faq")
            )
        ).all()
        for doc in stale:
            if doc.source_key not in seen_keys:
                db.delete(doc)
                stats["deleted_stale"] += 1
        if stats["deleted_stale"]:
            db.commit()

    return stats


def reindex_tag_embeddings(
    db: Session,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    batch_size: int | None = None,
    batch_pause_sec: float | None = None,
    request_pause_sec: float | None = None,
) -> dict[str, Any]:
    """Precompute embeddings for TagsOrm names (throttled)."""
    throttle = _throttle_params(
        limit=limit,
        batch_size=batch_size,
        batch_pause_sec=batch_pause_sec,
        request_pause_sec=request_pause_sec,
    )
    tags = list(
        db.scalars(
            select(TagsOrm).order_by(TagsOrm.id.asc()).limit(throttle["limit"])
        ).all()
    )
    stats: dict[str, Any] = {
        "tags": len(tags),
        "upserted": 0,
        "skipped": 0,
        "dry_run": dry_run,
        "limit": throttle["limit"],
        "batch_size": throttle["batch_size"],
        "stopped_reason": None,
    }
    pending: list[TagsOrm] = []
    for tag in tags:
        h = content_sha256(tag.name)
        existing = db.get(AiRagTagEmbeddingsOrm, tag.id)
        if existing is not None and existing.content_hash == h and existing.embedding:
            stats["skipped"] += 1
            continue
        pending.append(tag)

    if dry_run:
        stats["upserted"] = len(pending)
        return stats

    # Small embed groups so a 429 does not waste a large in-flight batch.
    embed_batch = min(throttle["batch_size"], 8)
    total_calls = (len(pending) + embed_batch - 1) // embed_batch or 1
    for call_i, i in enumerate(range(0, len(pending), embed_batch)):
        batch = pending[i : i + embed_batch]
        vecs = _embed_or_rate_limit(
            [t.name for t in batch],
            task_type="retrieval_document",
            stats=stats,
        )
        for tag, vec in zip(batch, vecs, strict=True):
            h = content_sha256(tag.name)
            row = db.get(AiRagTagEmbeddingsOrm, tag.id)
            if row is None:
                db.add(
                    AiRagTagEmbeddingsOrm(
                        tag_id=tag.id,
                        name=tag.name,
                        content_hash=h,
                        embedding=vec,
                        meta={},
                    )
                )
            else:
                row.name = tag.name
                row.content_hash = h
                row.embedding = vec
                row.updated_at = datetime.now(timezone.utc)
            stats["upserted"] += 1
        db.commit()
        logger.info(
            "rag tag embed batch %s-%s upserted=%s",
            i,
            i + len(batch),
            stats["upserted"],
        )
        _pause_between(
            index=call_i,
            total=total_calls,
            batch_size=throttle["batch_size"],
            batch_pause_sec=throttle["batch_pause_sec"],
            request_pause_sec=throttle["request_pause_sec"],
        )
    return stats


def _pin_tag_names(db: Session, pin_id: int) -> list[str]:
    rows = (
        db.execute(
            select(TagsOrm.name)
            .join(pins_tags, pins_tags.c.tag_id == TagsOrm.id)
            .where(pins_tags.c.pin_id == pin_id)
            .order_by(TagsOrm.name.asc())
        )
    ).all()
    return [r[0] for r in rows if r[0]]


def reindex_pins(
    db: Session,
    *,
    from_id: int | None = None,
    to_id: int | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    batch_size: int | None = None,
    batch_pause_sec: float | None = None,
    request_pause_sec: float | None = None,
) -> dict[str, Any]:
    """Index public pins as parent docs + child chunks (title/desc/tags)."""
    throttle = _throttle_params(
        limit=limit,
        batch_size=batch_size,
        batch_pause_sec=batch_pause_sec,
        request_pause_sec=request_pause_sec,
    )
    stmt = select(PinsOrm).order_by(PinsOrm.id.asc())
    if from_id is not None:
        stmt = stmt.where(PinsOrm.id >= from_id)
    if to_id is not None:
        stmt = stmt.where(PinsOrm.id <= to_id)
    stmt = stmt.limit(throttle["limit"])
    pins = list(db.scalars(stmt).all())

    stats: dict[str, Any] = {
        "pins": len(pins),
        "upserted": 0,
        "skipped": 0,
        "chunks": 0,
        "dry_run": dry_run,
        "limit": throttle["limit"],
        "batch_size": throttle["batch_size"],
        "from_id": from_id,
        "to_id": to_id,
        "stopped_reason": None,
        "last_pin_id": None,
    }

    for i, pin in enumerate(pins):
        stats["last_pin_id"] = pin.id
        tags = _pin_tag_names(db, pin.id)
        doc_hash = pin_document_hash(
            title=pin.title, description=pin.description, tag_names=tags
        )
        source_key = str(pin.id)
        existing = db.scalar(
            select(AiRagDocumentsOrm).where(
                AiRagDocumentsOrm.source_type == "pin",
                AiRagDocumentsOrm.source_key == source_key,
            )
        )
        if existing is not None and existing.content_hash == doc_hash:
            stats["skipped"] += 1
            _pause_between(
                index=i,
                total=len(pins),
                batch_size=throttle["batch_size"],
                batch_pause_sec=throttle["batch_pause_sec"],
                request_pause_sec=0.0,
            )
            continue

        children = build_pin_child_chunks(
            title=pin.title, description=pin.description, tag_names=tags
        )
        if not children:
            stats["skipped"] += 1
            continue

        if dry_run:
            stats["upserted"] += 1
            stats["chunks"] += len(children)
            continue

        body = "\n".join(
            [
                (pin.title or "").strip(),
                (pin.description or "").strip(),
                ", ".join(tags),
            ]
        )
        if existing is None:
            existing = AiRagDocumentsOrm(
                source_type="pin",
                source_key=source_key,
                title=(pin.title or f"pin-{pin.id}")[:300],
                path=f"/pin/{pin.id}",
                body=body,
                content_hash=doc_hash,
                meta={"pin_id": pin.id},
            )
            db.add(existing)
            db.flush()
        else:
            existing.title = (pin.title or f"pin-{pin.id}")[:300]
            existing.path = f"/pin/{pin.id}"
            existing.body = body
            existing.content_hash = doc_hash
            existing.meta = {**(existing.meta or {}), "pin_id": pin.id}
            existing.updated_at = datetime.now(timezone.utc)
            db.execute(
                delete(AiRagChunksOrm).where(AiRagChunksOrm.document_id == existing.id)
            )
            db.flush()

        embeddings = _embed_or_rate_limit(
            [c.content for c in children],
            task_type="retrieval_document",
            stats=stats,
        )
        for ch, vec in zip(children, embeddings, strict=True):
            db.add(
                AiRagChunksOrm(
                    document_id=existing.id,
                    chunk_index=ch.chunk_index,
                    chunk_kind=ch.chunk_kind,
                    heading=ch.heading,
                    content=ch.content,
                    content_hash=ch.content_hash,
                    embedding=vec,
                    meta={"pin_id": pin.id, "chunk_kind": ch.chunk_kind},
                )
            )
        stats["upserted"] += 1
        stats["chunks"] += len(children)
        db.commit()
        logger.info("rag reindex pin=%s chunks=%s", pin.id, len(children))
        _pause_between(
            index=i,
            total=len(pins),
            batch_size=throttle["batch_size"],
            batch_pause_sec=throttle["batch_pause_sec"],
            request_pause_sec=throttle["request_pause_sec"],
        )

    return stats
