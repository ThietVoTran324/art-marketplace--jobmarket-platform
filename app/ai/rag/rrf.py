"""Reciprocal Rank Fusion helpers."""

from __future__ import annotations

from typing import Hashable, Iterable, TypeVar

from app.config import settings

T = TypeVar("T", bound=Hashable)


def rrf_fuse(
    ranked_lists: Iterable[Iterable[T]],
    *,
    k: int | None = None,
) -> list[T]:
    """Fuse multiple ranked lists of ids via RRF. Higher score = better."""
    kk = int(k if k is not None else settings.AI_RAG_RRF_K or 60)
    scores: dict[T, float] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (kk + rank)
    return [item for item, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)]
