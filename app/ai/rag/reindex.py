"""Offline reindex: FAQ md, pin parent–child, tag catalog embeddings.

Throttling mirrors scripts/backfill_pin_ai_tags (limit + per-request/batch pauses)
so Gemini quota stops the run cleanly instead of failing mid-flight.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import String, cast, delete, select
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
    FaqArticlesOrm,
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


def _upsert_faq_document(
    db: Session,
    *,
    source_key: str,
    title: str,
    body: str,
    path: str | None,
    meta: dict[str, Any],
    dry_run: bool,
    stats: dict[str, Any],
) -> bool:
    """Upsert one FAQ doc+chunks. Returns True if embedded (not skipped)."""
    doc_hash = content_sha256(body)
    existing = db.scalar(
        select(AiRagDocumentsOrm).where(
            AiRagDocumentsOrm.source_type == "faq",
            AiRagDocumentsOrm.source_key == source_key,
        )
    )
    if existing is not None and existing.content_hash == doc_hash:
        stats["skipped"] += 1
        return False

    chunks = chunk_markdown(body)
    if dry_run:
        stats["upserted"] += 1
        stats["chunks"] += len(chunks)
        return True

    if existing is None:
        existing = AiRagDocumentsOrm(
            source_type="faq",
            source_key=source_key,
            title=title,
            path=path,
            body=body,
            content_hash=doc_hash,
            meta=meta,
        )
        db.add(existing)
        db.flush()
    else:
        existing.title = title
        existing.path = path
        existing.body = body
        existing.content_hash = doc_hash
        existing.meta = {**(existing.meta or {}), **meta}
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
    return True


def remove_faq_from_index(db: Session, slug: str) -> bool:
    """Delete indexed FAQ document (and chunks) for slug. Returns True if deleted."""
    doc = db.scalar(
        select(AiRagDocumentsOrm).where(
            AiRagDocumentsOrm.source_type == "faq",
            AiRagDocumentsOrm.source_key == slug,
        )
    )
    if doc is None:
        return False
    db.delete(doc)
    db.commit()
    return True


def reindex_faq_article(
    db: Session,
    slug: str,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Index one published CMS article; remove index if draft/missing."""
    stats: dict[str, Any] = {
        "slug": slug,
        "upserted": 0,
        "skipped": 0,
        "chunks": 0,
        "removed": 0,
        "dry_run": dry_run,
        "stopped_reason": None,
    }
    article = db.scalar(select(FaqArticlesOrm).where(FaqArticlesOrm.slug == slug))
    if article is None or article.status != "published":
        if not dry_run and remove_faq_from_index(db, slug):
            stats["removed"] = 1
        return stats

    body = article.body or ""
    title = (article.title or "").strip() or _title_from_markdown(body, slug)
    _upsert_faq_document(
        db,
        source_key=slug,
        title=title[:300],
        body=body,
        path=f"cms:faq:{slug}",
        meta={"cms": True, "faq_article_id": article.id},
        dry_run=dry_run,
        stats=stats,
    )
    return stats


def reindex_faq_from_cms(
    db: Session,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    batch_size: int | None = None,
    batch_pause_sec: float | None = None,
    request_pause_sec: float | None = None,
) -> dict[str, Any]:
    """Reindex all published CMS FAQ articles; prune stale faq vector docs."""
    throttle = _throttle_params(
        limit=limit,
        batch_size=batch_size,
        batch_pause_sec=batch_pause_sec,
        request_pause_sec=request_pause_sec,
    )
    all_articles = list(
        db.scalars(
            select(FaqArticlesOrm)
            .where(FaqArticlesOrm.status == "published")
            .order_by(FaqArticlesOrm.id.asc())
        ).all()
    )
    articles = all_articles[: throttle["limit"]]
    stats: dict[str, Any] = {
        "source": "cms",
        "articles": len(articles),
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
    for i, article in enumerate(articles):
        seen_keys.add(article.slug)
        body = article.body or ""
        title = (article.title or "").strip() or _title_from_markdown(body, article.slug)
        embedded = _upsert_faq_document(
            db,
            source_key=article.slug,
            title=title[:300],
            body=body,
            path=f"cms:faq:{article.slug}",
            meta={"cms": True, "faq_article_id": article.id},
            dry_run=dry_run,
            stats=stats,
        )
        _pause_between(
            index=i,
            total=len(articles),
            batch_size=throttle["batch_size"],
            batch_pause_sec=throttle["batch_pause_sec"],
            request_pause_sec=(throttle["request_pause_sec"] if embedded else 0.0),
        )

    if (
        not dry_run
        and stats.get("stopped_reason") is None
        and len(articles) == len(all_articles)
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
    """FAQ reindex: prefer published CMS articles; else legacy corpus markdown."""
    if not settings.AI_RAG_ENABLED and not dry_run:
        logger.warning("AI_RAG_ENABLED=false — reindex still runs when invoked explicitly")

    published_n = db.scalar(
        select(FaqArticlesOrm.id).where(FaqArticlesOrm.status == "published").limit(1)
    )
    if published_n is not None:
        return reindex_faq_from_cms(
            db,
            dry_run=dry_run,
            limit=limit,
            batch_size=batch_size,
            batch_pause_sec=batch_pause_sec,
            request_pause_sec=request_pause_sec,
        )

    throttle = _throttle_params(
        limit=limit,
        batch_size=batch_size,
        batch_pause_sec=batch_pause_sec,
        request_pause_sec=request_pause_sec,
    )
    all_files = list_faq_files(directory)
    files = all_files[: throttle["limit"]]
    stats: dict[str, Any] = {
        "source": "markdown",
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
        title = _title_from_markdown(raw, source_key)
        rel_path = f"app/ai/rag/corpus/{path.name}"
        embedded = _upsert_faq_document(
            db,
            source_key=source_key,
            title=title,
            body=raw,
            path=rel_path,
            meta={"corpus_file": path.name},
            dry_run=dry_run,
            stats=stats,
        )
        _pause_between(
            index=i,
            total=len(files),
            batch_size=throttle["batch_size"],
            batch_pause_sec=throttle["batch_pause_sec"],
            request_pause_sec=(throttle["request_pause_sec"] if embedded else 0.0),
        )

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
    missing_only: bool = False,
) -> dict[str, Any]:
    """Precompute embeddings for TagsOrm names (throttled)."""
    throttle = _throttle_params(
        limit=limit,
        batch_size=batch_size,
        batch_pause_sec=batch_pause_sec,
        request_pause_sec=request_pause_sec,
    )
    stats: dict[str, Any] = {
        "tags": 0,
        "upserted": 0,
        "skipped": 0,
        "dry_run": dry_run,
        "limit": throttle["limit"],
        "batch_size": throttle["batch_size"],
        "missing_only": missing_only,
        "stopped_reason": None,
    }
    pending: list[TagsOrm] = []
    if missing_only:
        # Scan in id order until we collect `limit` tags that need embed.
        all_tags = db.scalars(select(TagsOrm).order_by(TagsOrm.id.asc())).all()
        for tag in all_tags:
            h = content_sha256(tag.name)
            existing = db.get(AiRagTagEmbeddingsOrm, tag.id)
            if (
                existing is not None
                and existing.content_hash == h
                and existing.embedding is not None
            ):
                continue
            pending.append(tag)
            if len(pending) >= throttle["limit"]:
                break
        stats["tags"] = len(pending)
    else:
        tags = list(
            db.scalars(
                select(TagsOrm).order_by(TagsOrm.id.asc()).limit(throttle["limit"])
            ).all()
        )
        stats["tags"] = len(tags)
        for tag in tags:
            h = content_sha256(tag.name)
            existing = db.get(AiRagTagEmbeddingsOrm, tag.id)
            # embedding is a vector/array — never use truthiness (ambiguous).
            if (
                existing is not None
                and existing.content_hash == h
                and existing.embedding is not None
            ):
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
    missing_only: bool = False,
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
    if missing_only:
        indexed = select(AiRagDocumentsOrm.source_key).where(
            AiRagDocumentsOrm.source_type == "pin"
        )
        stmt = stmt.where(~cast(PinsOrm.id, String).in_(indexed))
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
        "missing_only": missing_only,
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


def reindex_rag_missing(
    db: Session,
    *,
    dry_run: bool = False,
    pin_limit: int | None = None,
    tag_limit: int | None = None,
) -> dict[str, Any]:
    """Sequential missing-only pins then tags (scheduled automation)."""
    pins_lim = (
        pin_limit
        if pin_limit is not None
        else int(settings.AI_RAG_AUTO_PIN_LIMIT or 50)
    )
    tags_lim = (
        tag_limit
        if tag_limit is not None
        else int(settings.AI_RAG_AUTO_TAG_LIMIT or 200)
    )
    out: dict[str, Any] = {"pins": None, "tags": None}
    out["pins"] = reindex_pins(
        db,
        dry_run=dry_run,
        limit=pins_lim,
        missing_only=True,
    )
    out["tags"] = reindex_tag_embeddings(
        db,
        dry_run=dry_run,
        limit=tags_lim,
        missing_only=True,
    )
    return out


def reindex_rag_pin(
    db: Session,
    pin_id: int,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Index exactly one pin (hook path)."""
    return reindex_pins(
        db,
        from_id=int(pin_id),
        to_id=int(pin_id),
        limit=1,
        dry_run=dry_run,
        missing_only=False,
        batch_size=1,
        batch_pause_sec=0.0,
    )


def reindex_rag_tag(
    db: Session,
    tag_id: int,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Embed exactly one catalog tag (hook path)."""
    tag = db.get(TagsOrm, int(tag_id))
    stats: dict[str, Any] = {
        "tag_id": int(tag_id),
        "upserted": 0,
        "skipped": 0,
        "dry_run": dry_run,
        "stopped_reason": None,
    }
    if tag is None:
        stats["skipped"] = 1
        stats["stopped_reason"] = "no_tag"
        return stats

    h = content_sha256(tag.name)
    existing = db.get(AiRagTagEmbeddingsOrm, tag.id)
    if (
        existing is not None
        and existing.content_hash == h
        and existing.embedding is not None
    ):
        stats["skipped"] = 1
        return stats

    if dry_run:
        stats["upserted"] = 1
        return stats

    vecs = _embed_or_rate_limit(
        [tag.name],
        task_type="retrieval_document",
        stats=stats,
    )
    vec = vecs[0]
    if existing is None:
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
        existing.name = tag.name
        existing.content_hash = h
        existing.embedding = vec
        existing.updated_at = datetime.now(timezone.utc)
    db.commit()
    stats["upserted"] = 1
    logger.info("rag reindex tag=%s", tag.id)
    return stats


def remove_rag_pin(db: Session, pin_id: int) -> dict[str, Any]:
    """Delete pin parent doc + chunks from RAG index."""
    source_key = str(int(pin_id))
    existing = db.scalar(
        select(AiRagDocumentsOrm).where(
            AiRagDocumentsOrm.source_type == "pin",
            AiRagDocumentsOrm.source_key == source_key,
        )
    )
    stats: dict[str, Any] = {
        "pin_id": int(pin_id),
        "deleted": False,
        "chunks_deleted": 0,
    }
    if existing is None:
        return stats
    chunk_res = db.execute(
        delete(AiRagChunksOrm).where(AiRagChunksOrm.document_id == existing.id)
    )
    stats["chunks_deleted"] = int(chunk_res.rowcount or 0)
    db.execute(delete(AiRagDocumentsOrm).where(AiRagDocumentsOrm.id == existing.id))
    db.commit()
    stats["deleted"] = True
    logger.info("rag remove pin=%s chunks=%s", pin_id, stats["chunks_deleted"])
    return stats
