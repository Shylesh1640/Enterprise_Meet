"""Enterprise Meet — Celery application and worker tasks."""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

# ── Celery App ────────────────────────────────────────────────────────────────

celery_app = Celery(
    "enterprise_meet",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.email_tasks",
        "app.workers.notification_tasks",
        "app.workers.recording_tasks",
        "app.workers.cleanup_tasks",
        "app.workers.reminder_tasks",
    ],
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
    task_reject_on_worker_lost=True,
    task_time_limit=300,       # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    result_expires=3600,       # 1 hour
)

# ── Beat Schedule ─────────────────────────────────────────────────────────────

celery_app.conf.beat_schedule = {
    "send-meeting-reminders-every-minute": {
        "task": "app.workers.reminder_tasks.check_upcoming_meetings",
        "schedule": 60.0,  # every 60 seconds
    },
    "cleanup-expired-sessions-hourly": {
        "task": "app.workers.cleanup_tasks.cleanup_expired_sessions",
        "schedule": 3600.0,
    },
    "cleanup-orphan-files-daily": {
        "task": "app.workers.cleanup_tasks.cleanup_orphan_files",
        "schedule": 86400.0,
    },
}
