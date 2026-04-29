from celery import Celery

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "velvic",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Stockholm",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
