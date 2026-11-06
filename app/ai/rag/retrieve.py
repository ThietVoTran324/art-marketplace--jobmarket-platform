"""FAQ + pin hybrid retrieve (vector + keyword + optional matched_tags → RRF)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag.embed import embed_query
from app.ai.rag.rrf import rrf_fuse
from app.config import settings
from app.postgresql.models import (
    AiRagChunksOrm,
    AiRagDocumentsOrm,
    PinsOrm,
    TagsOrm,
    pins_tags,
)


def _frontend_origin() -> str:
    return (settings.FRONTEND_DOMAIN or "").rstrip("/")


async def retrieve_knowledge(
    db: AsyncSession,
    *,
    query: str,
    limit: int | None = None,
    scope: str = "all",
    matched_tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    scope: faq | pin | all
    matched_tags: optional catalog tag names from intent skill (boost pin branch).
    """
    if not settings.AI_RAG_ENABLED:
        return {"chunks": [], "pins": [], "note": "ai_rag_disabled"}

    q = (query or "").strip()
    if not q:
        return {"chunks": [], "pins": [], "note": "empty_query"}

    top_k = limit if limit is not None else settings.AI_RAG_TOP_K
    try:
        top_k = max(1, min(int(top_k), 10))
    except (TypeError, ValueError):
        top_k = settings.AI_RAG_TOP_K

    scope_n = (scope or "all").strip().lower()
    if scope_n not in {"faq", "pin", "all"}:
        scope_n = "all"

    faq_chunks: list[dict[str, Any]] = []
    pin_hits: list[dict[str, Any]] = []

    if scope_n in {"faq", "all"}:
        faq_chunks = await _vector_faq(db, query=q, top_k=top_k)
    if scope_n in {"pin", "all"}:
        pin_hits = await _hybrid_pins(
            db, query=q, top_k=top_k, matched_tags=matched_tags or []
        )

    # Present pin hits also as cite-able "chunks" for FE/meta consistency
    pin_as_chunks = [_pin_hit_to_chunk(p) for p in pin_hits]
    chunks = faq_chunks + pin_as_chunks
    note = "ok" if chunks or pin_hits else "no_matches"
    return {
        "chunks": chunks[: top_k * 2],
        "pins": pin_hits,
        "faq_chunks": faq_chunks,
        "note": note,
        "query": q,
        "scope": scope_n,
        "matched_tags_used": matched_tags or [],
    }


async def _vector_faq(
    db: AsyncSession, *, query: str, top_k: int
) -> list[dict[str, Any]]:
    try:
        qvec = embed_query(query)
    except Exception as exc:  # noqa: BLE001
        return [{"error": "embed_failed", "detail": str(exc)[:200]}]

    distance = AiRagChunksOrm.embedding.cosine_distance(qvec)
    stmt = (
        select(
            AiRagChunksOrm.id,
            AiRagChunksOrm.chunk_index,
            AiRagChunksOrm.chunk_kind,
            AiRagChunksOrm.heading,
            AiRagChunksOrm.content,
            AiRagDocumentsOrm.id.label("document_id"),
            AiRagDocumentsOrm.source_type,
            AiRagDocumentsOrm.source_key,
            AiRagDocumentsOrm.title,
            AiRagDocumentsOrm.path,
            distance.label("distance"),
        )
        .join(AiRagDocumentsOrm, AiRagDocumentsOrm.id == AiRagChunksOrm.document_id)
        .where(
            AiRagChunksOrm.embedding.is_not(None),
            AiRagDocumentsOrm.source_type == "faq",
        )
        .order_by(distance)
        .limit(top_k)
    )
    rows = (await db.execute(stmt)).all()
    min_score = float(settings.AI_RAG_MIN_SCORE or 0.0)
    out: list[dict[str, Any]] = []
    for r in rows:
        dist = float(r.distance or 0.0)
        score = 1.0 - dist
        if min_score > 0 and score < min_score:
            continue
        # FAQ lives in corpus markdown only — no frontend route. Do not expose
        # filesystem paths as path/url (FE would navigate to /null or /app/...).
        out.append(
            {
                "chunk_id": r.id,
                "document_id": r.document_id,
                "source_type": "faq",
                "source_key": r.source_key,
                "title": r.title,
                "heading": r.heading,
                "chunk_kind": r.chunk_kind,
                "content": (r.content or "")[:1200],
                "score": round(score, 4),
                "path": None,
                "url": None,
                "cite_label": r.heading or r.title,
                "source_ref": f"faq:{r.source_key}",
            }
        )
    return out


async def _hybrid_pins(
    db: AsyncSession,
    *,
    query: str,
    top_k: int,
    matched_tags: list[str],
) -> list[dict[str, Any]]:
    vector_ranked = await _vector_pin_ids(db, query=query, limit=max(top_k * 3, 15))
    keyword_ranked = await _keyword_pin_ids(db, query=query, limit=max(top_k * 3, 15))
    tag_ranked = await _tag_pin_ids(db, matched_tags=matched_tags, limit=max(top_k * 3, 15))

    lists = [vector_ranked, keyword_ranked]
    if tag_ranked:
        lists.append(tag_ranked)
    fused_ids = rrf_fuse(lists)[:top_k]
    if not fused_ids:
        return []

    # Preserve fused order
    rows = (
        await db.execute(
            select(PinsOrm.id, PinsOrm.title, PinsOrm.description).where(
                PinsOrm.id.in_(fused_ids)
            )
        )
    ).all()
    by_id = {r.id: r for r in rows}
    origin = _frontend_origin()
    hits: list[dict[str, Any]] = []
    for i, pid in enumerate(fused_ids):
        row = by_id.get(pid)
        if row is None:
            continue
        hits.append(
            {
                "id": pid,
                "title": row.title,
                "description": (row.description or "")[:160],
                "path": f"/pin/{pid}",
                "url": f"{origin}/pin/{pid}",
                "thumb_url": f"{origin}/api/pins/upload/{pid}",
                "rrf_rank": i + 1,
                "source_type": "pin",
            }
        )
    return hits


async def _vector_pin_ids(
    db: AsyncSession, *, query: str, limit: int
) -> list[int]:
    try:
        qvec = embed_query(query)
    except Exception:
        return []
    distance = AiRagChunksOrm.embedding.cosine_distance(qvec)
    stmt = (
        select(AiRagDocumentsOrm.source_key, distance.label("distance"))
        .join(AiRagChunksOrm, AiRagChunksOrm.document_id == AiRagDocumentsOrm.id)
        .where(
            AiRagDocumentsOrm.source_type == "pin",
            AiRagChunksOrm.embedding.is_not(None),
        )
        .order_by(distance)
        .limit(limit * 4)
    )
    rows = (await db.execute(stmt)).all()
    ordered: list[int] = []
    seen: set[int] = set()
    for r in rows:
        try:
            pid = int(r.source_key)
        except (TypeError, ValueError):
            continue
        if pid in seen:
            continue
        seen.add(pid)
        ordered.append(pid)
        if len(ordered) >= limit:
            break
    return ordered


async def _keyword_pin_ids(
    db: AsyncSession, *, query: str, limit: int
) -> list[int]:
    pattern = f"%{query}%"
    tag_pin_ids = (
        select(pins_tags.c.pin_id)
        .join(TagsOrm, TagsOrm.id == pins_tags.c.tag_id)
        .where(TagsOrm.name.ilike(pattern))
    )
    stmt = (
        select(PinsOrm.id)
        .where(
            or_(
                PinsOrm.title.ilike(pattern),
                PinsOrm.description.ilike(pattern),
                PinsOrm.id.in_(tag_pin_ids),
            )
        )
        .order_by(PinsOrm.id.desc())
        .limit(limit)
    )
    return [int(r[0]) for r in (await db.execute(stmt)).all()]


async def _tag_pin_ids(
    db: AsyncSession, *, matched_tags: list[str], limit: int
) -> list[int]:
    names = [t.strip() for t in matched_tags if t and str(t).strip()]
    if not names:
        return []
    ors = [TagsOrm.name.ilike(n) for n in names]
    stmt = (
        select(pins_tags.c.pin_id)
        .join(TagsOrm, TagsOrm.id == pins_tags.c.tag_id)
        .where(or_(*ors))
        .limit(limit * 5)
    )
    rows = (await db.execute(stmt)).all()
    ordered: list[int] = []
    seen: set[int] = set()
    for r in rows:
        pid = int(r[0])
        if pid in seen:
            continue
        seen.add(pid)
        ordered.append(pid)
        if len(ordered) >= limit:
            break
    return ordered


def _pin_hit_to_chunk(pin: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": None,
        "source_type": "pin",
        "source_key": str(pin["id"]),
        "title": pin.get("title"),
        "heading": pin.get("title"),
        "content": pin.get("description") or "",
        "score": None,
        "path": pin.get("path"),
        "url": pin.get("url"),
        "thumb_url": pin.get("thumb_url"),
        "cite_label": pin.get("title") or f"pin:{pin['id']}",
        "source_ref": f"pin:{pin['id']}",
        "pin_id": pin["id"],
    }
