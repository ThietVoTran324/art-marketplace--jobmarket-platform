"""Embedding providers — default Gemini; Jina via AI_RAG_EMBED_PROVIDER."""

from __future__ import annotations

from typing import Sequence

import google.generativeai as genai
import httpx

from app.config import settings
from app.logger import logger


def _configure_gemini() -> None:
    if not settings.AI_GEMINI_API_KEY:
        raise RuntimeError("AI_GEMINI_API_KEY is empty")
    genai.configure(api_key=settings.AI_GEMINI_API_KEY)


def embed_texts(
    texts: Sequence[str],
    *,
    task_type: str = "retrieval_document",
) -> list[list[float]]:
    provider = (settings.AI_RAG_EMBED_PROVIDER or "gemini").strip().lower()
    if provider == "gemini":
        return _embed_gemini(texts, task_type=task_type)
    if provider == "jina":
        return _embed_jina(texts)
    raise RuntimeError(f"unsupported AI_RAG_EMBED_PROVIDER={provider!r}")


def embed_query(text: str) -> list[float]:
    return embed_texts([text], task_type="retrieval_query")[0]


def _embed_gemini(texts: Sequence[str], *, task_type: str) -> list[list[float]]:
    _configure_gemini()
    model = settings.AI_RAG_EMBED_MODEL or "models/text-embedding-004"
    out: list[list[float]] = []
    for t in texts:
        cleaned = (t or "").strip()
        if not cleaned:
            out.append([0.0] * settings.AI_RAG_EMBED_DIMS)
            continue
        kwargs: dict = {
            "model": model,
            "content": cleaned,
            "task_type": task_type,
        }
        # gemini-embedding-001 defaults to 3072; pin to configured dims when supported.
        if settings.AI_RAG_EMBED_DIMS:
            kwargs["output_dimensionality"] = int(settings.AI_RAG_EMBED_DIMS)
        try:
            result = genai.embed_content(**kwargs)
        except TypeError:
            kwargs.pop("output_dimensionality", None)
            result = genai.embed_content(**kwargs)
        vec = list(result["embedding"])
        if len(vec) != settings.AI_RAG_EMBED_DIMS:
            logger.warning(
                "embed dims mismatch got=%s expected=%s model=%s",
                len(vec),
                settings.AI_RAG_EMBED_DIMS,
                model,
            )
        out.append(vec)
    return out


def _embed_jina(texts: Sequence[str]) -> list[list[float]]:
    key = (settings.AI_RAG_JINA_API_KEY or "").strip()
    if not key:
        raise RuntimeError("AI_RAG_JINA_API_KEY is empty (N-rag-jina-live)")
    model = settings.AI_RAG_EMBED_MODEL or "jina-embeddings-v3"
    payload = {
        "model": model,
        "input": [((t or "").strip() or " ") for t in texts],
        "task": "retrieval.passage",
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            "https://api.jina.ai/v1/embeddings",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    items = sorted(data.get("data") or [], key=lambda x: x.get("index", 0))
    return [list(item["embedding"]) for item in items]
