"""Celery tasks for AI auto-tag and RAG reindex (thin wrappers)."""

from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from app.celery.celery_app import celery_instance
from app.config import settings
from app.logger import logger
from app.postgresql.database import get_sync_db


@celery_instance.task(
    name="app.ai.tasks.analyze_pin_image",
    queue="ai_auto_tag",
    acks_late=True,
    # Soft/hard limits: Gemini can be slow; avoid infinite hang.
    # Gemini from this env can take minutes (cold/new-key path); keep above observed ~250s text call.
    soft_time_limit=600,
    time_limit=660,
)
def analyze_pin_image(pin_id: int):
    """Load pin media → Gemini → merge tags (+only). Fair queue: ai_auto_tag."""
    if not settings.AI_AUTO_TAG_ENABLED:
        return {"status": "skipped", "reason": "disabled"}

    try:
        db = next(get_sync_db())
    except SQLAlchemyError:
        raise

    try:
        from app.ai.services.auto_tag import run_auto_tag

        result = run_auto_tag(db, pin_id)
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        logger.error("analyze_pin_image failed pin_id=%s: %s", pin_id, exc, exc_info=True)
        # Persist failed status after rollback of tag writes
        try:
            from app.ai.services.auto_tag import upsert_analysis

            upsert_analysis(db, pin_id, status="failed", error_message=str(exc)[:400])
            db.commit()
        except Exception as inner:
            db.rollback()
            logger.error("failed to persist ai analysis status: %s", inner, exc_info=True)
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error("Error closing db session: %s", e, exc_info=True)


@celery_instance.task(
    name="app.ai.tasks.reindex_rag_corpus",
    soft_time_limit=600,
    time_limit=660,
)
def reindex_rag_corpus(mode: str = "faq"):
    """Offline RAG reindex. mode: faq | tags | pins | all. Does not block chat."""
    try:
        db = next(get_sync_db())
    except SQLAlchemyError:
        raise
    try:
        from app.ai.rag.reindex import (
            ReindexRateLimited,
            reindex_faq_corpus,
            reindex_pins,
            reindex_tag_embeddings,
        )

        out: dict = {}
        m = (mode or "faq").lower()
        try:
            if m in {"faq", "all"}:
                out["faq"] = reindex_faq_corpus(db, dry_run=False)
            if m in {"tags", "all"}:
                out["tags"] = reindex_tag_embeddings(db, dry_run=False)
            if m in {"pins", "all"}:
                out["pins"] = reindex_pins(db, dry_run=False)
            return out
        except ReindexRateLimited as exc:
            db.rollback()
            out["stopped_reason"] = "rate_limit"
            out["partial"] = exc.stats
            logger.warning("reindex_rag_corpus rate-limited: %s stats=%s", exc, out)
            return out
    except Exception as exc:
        db.rollback()
        logger.error("reindex_rag_corpus failed: %s", exc, exc_info=True)
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error("Error closing db session: %s", e, exc_info=True)


@celery_instance.task(
    name="app.ai.tasks.reindex_rag_missing",
    queue="ai_auto_tag",
    soft_time_limit=1800,
    time_limit=1860,
)
def reindex_rag_missing_task():
    """Scheduled job: reindex missing pins then missing/stale tags."""
    if not settings.AI_RAG_AUTO_ENABLED:
        logger.info("reindex_rag_missing skipped — AI_RAG_AUTO_ENABLED=false")
        return {"status": "skipped", "reason": "disabled"}

    try:
        db = next(get_sync_db())
    except SQLAlchemyError:
        raise
    try:
        from app.ai.rag.reindex import ReindexRateLimited, reindex_rag_missing

        try:
            out = reindex_rag_missing(db, dry_run=False)
            logger.info("reindex_rag_missing done: %s", out)
            return out
        except ReindexRateLimited as exc:
            db.rollback()
            logger.warning("reindex_rag_missing rate-limited: %s", exc)
            return {"stopped_reason": "rate_limit", "partial": exc.stats}
    except Exception as exc:
        db.rollback()
        logger.error("reindex_rag_missing failed: %s", exc, exc_info=True)
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error("Error closing db session: %s", e, exc_info=True)


@celery_instance.task(
    name="app.ai.tasks.reindex_rag_pin",
    queue="ai_auto_tag",
    soft_time_limit=600,
    time_limit=660,
)
def reindex_rag_pin_task(pin_id: int):
    """Reindex one pin into RAG."""
    if not settings.AI_RAG_HOOK_ENABLED:
        return {"status": "skipped", "reason": "disabled"}
    try:
        db = next(get_sync_db())
    except SQLAlchemyError:
        raise
    try:
        from app.ai.rag.reindex import ReindexRateLimited, reindex_rag_pin

        try:
            out = reindex_rag_pin(db, int(pin_id), dry_run=False)
            logger.info("reindex_rag_pin done pin_id=%s: %s", pin_id, out)
            return out
        except ReindexRateLimited as exc:
            db.rollback()
            logger.warning("reindex_rag_pin rate-limited pin_id=%s: %s", pin_id, exc)
            return {"stopped_reason": "rate_limit", "partial": exc.stats, "pin_id": pin_id}
    except Exception as exc:
        db.rollback()
        logger.error("reindex_rag_pin failed pin_id=%s: %s", pin_id, exc, exc_info=True)
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error("Error closing db session: %s", e, exc_info=True)


@celery_instance.task(
    name="app.ai.tasks.reindex_rag_tag",
    queue="ai_auto_tag",
    soft_time_limit=300,
    time_limit=360,
)
def reindex_rag_tag_task(tag_id: int):
    """Embed one catalog tag into RAG."""
    if not settings.AI_RAG_HOOK_ENABLED:
        return {"status": "skipped", "reason": "disabled"}
    try:
        db = next(get_sync_db())
    except SQLAlchemyError:
        raise
    try:
        from app.ai.rag.reindex import ReindexRateLimited, reindex_rag_tag

        try:
            out = reindex_rag_tag(db, int(tag_id), dry_run=False)
            logger.info("reindex_rag_tag done tag_id=%s: %s", tag_id, out)
            return out
        except ReindexRateLimited as exc:
            db.rollback()
            logger.warning("reindex_rag_tag rate-limited tag_id=%s: %s", tag_id, exc)
            return {"stopped_reason": "rate_limit", "partial": exc.stats, "tag_id": tag_id}
    except Exception as exc:
        db.rollback()
        logger.error("reindex_rag_tag failed tag_id=%s: %s", tag_id, exc, exc_info=True)
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error("Error closing db session: %s", e, exc_info=True)


@celery_instance.task(
    name="app.ai.tasks.remove_rag_pin",
    queue="ai_auto_tag",
    soft_time_limit=120,
    time_limit=180,
)
def remove_rag_pin_task(pin_id: int):
    """Remove pin doc/chunks from RAG after delete."""
    if not settings.AI_RAG_HOOK_ENABLED:
        return {"status": "skipped", "reason": "disabled"}
    try:
        db = next(get_sync_db())
    except SQLAlchemyError:
        raise
    try:
        from app.ai.rag.reindex import remove_rag_pin

        out = remove_rag_pin(db, int(pin_id))
        logger.info("remove_rag_pin done pin_id=%s: %s", pin_id, out)
        return out
    except Exception as exc:
        db.rollback()
        logger.error("remove_rag_pin failed pin_id=%s: %s", pin_id, exc, exc_info=True)
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error("Error closing db session: %s", e, exc_info=True)


@celery_instance.task(
    name="app.ai.tasks.reindex_faq_article",
    soft_time_limit=600,
    time_limit=660,
)
def reindex_faq_article_task(slug: str):
    """Reindex one FAQ CMS slug (or remove from index if not published)."""
    try:
        db = next(get_sync_db())
    except SQLAlchemyError:
        raise
    try:
        from app.ai.rag.reindex import ReindexRateLimited, reindex_faq_article

        try:
            return reindex_faq_article(db, slug, dry_run=False)
        except ReindexRateLimited as exc:
            db.rollback()
            logger.warning("reindex_faq_article rate-limited slug=%s: %s", slug, exc)
            return {"stopped_reason": "rate_limit", "partial": exc.stats, "slug": slug}
    except Exception as exc:
        db.rollback()
        logger.error("reindex_faq_article failed slug=%s: %s", slug, exc, exc_info=True)
        raise
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error("Error closing db session: %s", e, exc_info=True)
