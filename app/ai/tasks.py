"""Celery tasks for AI auto-tag (thin wrappers around app.ai.services)."""

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
