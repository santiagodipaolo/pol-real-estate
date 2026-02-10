"""Celery application instance and beat schedule configuration.

The broker and result backend both point at the Redis instance defined in
``settings.REDIS_URL``.  Two periodic tasks are registered:

- **fetch-currency-rates** -- fetches live dollar exchange rates from DolarAPI
  every 15 minutes.
- **compute-daily-snapshots** -- aggregates listing statistics per barrio at
  03:00 UTC every day.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "pol_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# ---------------------------------------------------------------------------
# Autodiscover task modules inside the ``app.tasks`` package
# ---------------------------------------------------------------------------
celery_app.autodiscover_tasks(["app.tasks"])

# ---------------------------------------------------------------------------
# Beat schedule (periodic tasks)
# ---------------------------------------------------------------------------
celery_app.conf.beat_schedule = {
    "fetch-currency-rates-every-15-min": {
        "task": "app.tasks.currency_tasks.fetch_and_save_rates",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "default"},
    },
    "compute-daily-snapshots-at-3am": {
        "task": "app.tasks.snapshot_tasks.compute_daily_snapshots",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "default"},
    },
}
