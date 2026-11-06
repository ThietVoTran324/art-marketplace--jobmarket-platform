"""Offline reindex: FAQ md, pin parent–child, tag catalog embeddings."""

from __future__ import annotations

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


def reindex_faq_corpus(
    db: Session,
    *,
    directory: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not settings.AI_RAG_ENABLED and not dry_run:
        logger.warning("AI_RAG_ENABLED=false — reindex still runs when invoked explicitly")

    files = list_faq_files(directory)
    stats = {
        "files": len(files),
        "upserted": 0,
        "skipped": 0,
        "chunks": 0,
        "deleted_stale": 0,
        "dry_run": dry_run,
    }
    seen_keys: set[str] = set()

    for path in files:
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

        embeddings = embed_texts(
            [c.content for c in chunks], task_type="retrieval_document"
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

    if not dry_run:
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
    batch_size: int = 32,
) -> dict[str, Any]:
    """Precompute embeddings for all TagsOrm names."""
    tags = list(db.scalars(select(TagsOrm).order_by(TagsOrm.id.asc())).all())
    stats = {
        "tags": len(tags),
        "upserted": 0,
        "skipped": 0,
        "dry_run": dry_run,
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

    for i in range(0, len(pending), batch_size):
        batch = pending[i : i + batch_size]
        vecs = embed_texts([t.name for t in batch], task_type="retrieval_document")
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
) -> dict[str, Any]:
    """Index public pins as parent docs + child chunks (title/desc/tags)."""
    stmt = select(PinsOrm).order_by(PinsOrm.id.asc())
    if from_id is not None:
        stmt = stmt.where(PinsOrm.id >= from_id)
    if to_id is not None:
        stmt = stmt.where(PinsOrm.id <= to_id)
    if limit is not None:
        stmt = stmt.limit(max(1, int(limit)))
    pins = list(db.scalars(stmt).all())

    stats = {
        "pins": len(pins),
        "upserted": 0,
        "skipped": 0,
        "chunks": 0,
        "dry_run": dry_run,
    }

    for pin in pins:
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

        embeddings = embed_texts(
            [c.content for c in children], task_type="retrieval_document"
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

    return stats
