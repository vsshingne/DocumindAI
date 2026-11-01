"""Worker bootstrap. Document tasks are introduced in the ingestion milestone."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("documind", broker=settings.redis_url.get_secret_value())
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 3600},
    task_soft_time_limit=1500,
    task_time_limit=1800,
    timezone="UTC",
    enable_utc=True,
)
