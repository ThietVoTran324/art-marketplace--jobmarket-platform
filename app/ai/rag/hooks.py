"""Enqueue helpers for RAG index hooks. No-op unless AI_RAG_HOOK_ENABLED."""

from __future__ import annotations

from app.config import settings
from app.logger import logger


def enqueue_rag_pin(pin_id: int) -> bool:
    if not settings.AI_RAG_HOOK_ENABLED:
        return False
    from app.ai.tasks import reindex_rag_pin_task

    reindex_rag_pin_task.delay(int(pin_id))
    logger.info("rag hook enqueued pin_id=%s", pin_id)
    return True


def enqueue_rag_tag(tag_id: int) -> bool:
    if not settings.AI_RAG_HOOK_ENABLED:
        return False
    from app.ai.tasks import reindex_rag_tag_task

    reindex_rag_tag_task.delay(int(tag_id))
    logger.info("rag hook enqueued tag_id=%s", tag_id)
    return True


def enqueue_remove_rag_pin(pin_id: int) -> bool:
    if not settings.AI_RAG_HOOK_ENABLED:
        return False
    from app.ai.tasks import remove_rag_pin_task

    remove_rag_pin_task.delay(int(pin_id))
    logger.info("rag hook enqueued remove pin_id=%s", pin_id)
    return True


def enqueue_rag_tag_rename(tag_id: int) -> bool:
    """Reindex a tag after rename (same path as new-tag embed)."""
    return enqueue_rag_tag(tag_id)
