from app.config import settings

broker_url = settings.REDIS_URL_CELERY_BROKER
result_backend = settings.REDIS_URL_CELERY_RESULT
redbeat_redis_url = settings.REDIS_URL_CELERY_REDBEAT

beat_scheduler = "redbeat.RedBeatScheduler"

task_serializer = "json"
accept_content = ["json"]
result_expires = 3600  # Task result storage duration (1 hour)
timezone = "UTC"
enable_utc = True
broker_connection_retry_on_startup = True

# Fair Dispatch for heavy AI jobs is enforced on the dedicated worker
# (celery-worker-ai: -Q ai_auto_tag -c 1 --prefetch-multiplier=1).
# Keep main worker defaults so email/preview stay snappy.
task_create_missing_queues = True
task_default_queue = "celery"
task_routes = {
    "app.ai.tasks.analyze_pin_image": {"queue": "ai_auto_tag"},
}
