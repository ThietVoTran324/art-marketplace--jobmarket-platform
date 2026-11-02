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
}
