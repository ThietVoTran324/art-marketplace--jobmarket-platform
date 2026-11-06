"""Intent → English predicted tags → match against tag catalog (read-only)."""

from __future__ import annotations

import json
from typing import Any

import google.generativeai as genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.ai.rag.embed import embed_texts
from app.ai.services.auto_tag import normalize_tag_name
from app.config import settings
from app.logger import logger
from app.postgresql.models import AiRagTagEmbeddingsOrm

INTENT_SYSTEM = """You map user image-search intent to platform tag tokens.

Platform tags are English, lowercase, kebab-case (same as auto-tag), e.g. sports-car, concept-art, serene, hanoi, morning.

Rules:
1. Output JSON only: {"reasoning":"...","predicted_tags":["..."]}
2. predicted_tags: 0 to 4 items max. Prefer nouns/adjectives, short kebab-case. No sentences.
3. ANY user language (Vietnamese, English, slang, mixed) → translate/map to English tags only.
   Examples: chill→serene/relaxing; suy/lụy→lonely/sad; healing→nature/serene; flex→luxury.
4. If the query is garbage or has no visual intent, return predicted_tags: [].
5. Never invent brand/person names unless clearly requested. Never output Vietnamese tag tokens.
"""

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "predicted_tags": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["reasoning", "predicted_tags"],
}


def _configure() -> None:
    if not settings.AI_GEMINI_API_KEY:
        raise RuntimeError("AI_GEMINI_API_KEY is empty")
    genai.configure(api_key=settings.AI_GEMINI_API_KEY)


def predict_tags_from_query(query: str) -> dict[str, Any]:
    """LLM structured intent parse. Does NOT write tags to DB."""
    text = (query or "").strip()
    if not text:
        return {"reasoning": "empty", "predicted_tags": []}

    _configure()
    model_name = (
        settings.AI_RAG_INTENT_MODEL
        or settings.AI_CHAT_MODEL
        or settings.AI_GEMINI_MODEL
    )
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=INTENT_SYSTEM,
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
            max_output_tokens=256,
        ),
    )
    response = model.generate_content(
        f"User search request:\n{text}\n\nReturn JSON now."
    )
    raw = (response.text or "").strip()
    if not raw:
        return {"reasoning": "empty_model", "predicted_tags": []}
    data = json.loads(raw)
    max_n = max(1, int(settings.AI_RAG_PREDICTED_TAGS_MAX or 4))
    predicted: list[str] = []
    seen: set[str] = set()
    for item in data.get("predicted_tags") or []:
        norm = normalize_tag_name(str(item))
        if not norm or norm in seen:
            continue
        seen.add(norm)
        predicted.append(norm)
        if len(predicted) >= max_n:
            break
    return {
        "reasoning": str(data.get("reasoning") or "")[:400],
        "predicted_tags": predicted,
    }


async def match_predicted_to_catalog(
    db: AsyncSession,
    predicted_tags: list[str],
) -> list[dict[str, Any]]:
    """Embed predicted tags and cosine-match precomputed catalog embeddings."""
    if not predicted_tags:
        return []

    catalog = (
        await db.execute(
            select(
                AiRagTagEmbeddingsOrm.tag_id,
                AiRagTagEmbeddingsOrm.name,
                AiRagTagEmbeddingsOrm.embedding,
            ).where(AiRagTagEmbeddingsOrm.embedding.is_not(None))
        )
    ).all()
    if not catalog:
        # Fallback: exact/normalized name match against embeddings table empty → Tags via ILIKE later
        return []

    try:
        pred_vecs = embed_texts(predicted_tags, task_type="retrieval_query")
    except Exception as exc:  # noqa: BLE001
        logger.warning("intent tag embed failed: %s", exc)
        return []

    min_score = float(settings.AI_RAG_TAG_MATCH_MIN_SCORE or 0.62)
    max_matched = max(1, int(settings.AI_RAG_MATCHED_TAGS_MAX or 8))
    scored: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    for pred, pvec in zip(predicted_tags, pred_vecs, strict=True):
        best: tuple[float, Any] | None = None
        for row in catalog:
            cvec = row.embedding
            if not cvec:
                continue
            # cosine similarity
            score = _cosine(pvec, list(cvec))
            if best is None or score > best[0]:
                best = (score, row)
        if best is None or best[0] < min_score:
            continue
        row = best[1]
        if row.tag_id in seen_ids:
            continue
        seen_ids.add(row.tag_id)
        scored.append(
            {
                "tag_id": row.tag_id,
                "name": row.name,
                "score": round(best[0], 4),
                "from_predicted": pred,
            }
        )
        if len(scored) >= max_matched:
            break

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:max_matched]


def match_predicted_to_catalog_sync(
    db: Session,
    predicted_tags: list[str],
) -> list[dict[str, Any]]:
    """Sync variant for scripts/tests."""
    if not predicted_tags:
        return []
    catalog = (
        db.execute(
            select(
                AiRagTagEmbeddingsOrm.tag_id,
                AiRagTagEmbeddingsOrm.name,
                AiRagTagEmbeddingsOrm.embedding,
            ).where(AiRagTagEmbeddingsOrm.embedding.is_not(None))
        )
    ).all()
    if not catalog:
        return []
    pred_vecs = embed_texts(predicted_tags, task_type="retrieval_query")
    min_score = float(settings.AI_RAG_TAG_MATCH_MIN_SCORE or 0.62)
    max_matched = max(1, int(settings.AI_RAG_MATCHED_TAGS_MAX or 8))
    scored: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for pred, pvec in zip(predicted_tags, pred_vecs, strict=True):
        best: tuple[float, Any] | None = None
        for row in catalog:
            if not row.embedding:
                continue
            score = _cosine(pvec, list(row.embedding))
            if best is None or score > best[0]:
                best = (score, row)
        if best is None or best[0] < min_score:
            continue
        row = best[1]
        if row.tag_id in seen_ids:
            continue
        seen_ids.add(row.tag_id)
        scored.append(
            {
                "tag_id": row.tag_id,
                "name": row.name,
                "score": round(best[0], 4),
                "from_predicted": pred,
            }
        )
        if len(scored) >= max_matched:
            break
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:max_matched]


def _cosine(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for i in range(n):
        dot += a[i] * b[i]
        na += a[i] * a[i]
        nb += b[i] * b[i]
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / ((na**0.5) * (nb**0.5))
