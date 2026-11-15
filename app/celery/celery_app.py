from datetime import timedelta  # noqa

from celery import Celery
from celery.schedules import crontab

celery_instance = Celery(
    "tasks",
    include=["app.celery.tasks", "app.ai.tasks"],
)

celery_instance.config_from_object("app.celery.celeryconfig-redis")

celery_instance.conf.beat_schedule = {
    "mail-adds": {
        "task": "app.celery.tasks.send_email_adds",
        "schedule": crontab(hour=10, minute=0, day_of_week="sunday"),
        # "schedule": timedelta(seconds=20),
    },
    "cancel-expired-pending-orders": {
        "task": "app.celery.tasks.cancel_expired_pending_orders",
        "schedule": timedelta(minutes=5),
    },
    # Daily missing pin/tag RAG reindex (no-op unless AI_RAG_AUTO_ENABLED)
    "rag-reindex-missing": {
        "task": "app.ai.tasks.reindex_rag_missing",
        "schedule": crontab(hour=2, minute=0),  # 02:00 UTC daily
    },
}
