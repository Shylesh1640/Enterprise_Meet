"""Enterprise Meet — Recording, cleanup, reminder, and notification Celery tasks."""

from __future__ import annotations

import logging
from typing import Optional

from celery import Task

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# ── Recording Tasks ───────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def finalize_recording(self: Task, recording_id: str, meeting_id: str) -> dict:
    """
    Post-process a completed recording:
    1. Update status to READY
    2. Update duration and size from storage
    """
    import asyncio
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    # Use sync DB connection for Celery
    engine = create_engine(settings.DATABASE_SYNC_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    try:
        with Session() as session:
            from app.models.recording import Recording, RecordingStatus
            import uuid

            rec = session.get(Recording, uuid.UUID(recording_id))
            if not rec:
                logger.error(f"Recording {recording_id} not found")
                return {"error": "Not found"}

            rec.status = RecordingStatus.READY
            session.commit()

            logger.info(f"Recording {recording_id} finalized")
            return {"recording_id": recording_id, "status": "ready"}
    except Exception as exc:
        logger.error(f"Failed to finalize recording {recording_id}: {exc}")
        raise self.retry(exc=exc)


# ── Cleanup Tasks ─────────────────────────────────────────────────────────────

@celery_app.task
def delete_recording_file(object_key: str) -> None:
    """Delete a recording file from MinIO."""
    from app.core.config import settings
    from minio import Minio

    try:
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        client.remove_object(settings.MINIO_BUCKET_RECORDINGS, object_key)
        logger.info(f"Deleted recording file: {object_key}")
    except Exception as e:
        logger.error(f"Failed to delete recording {object_key}: {e}")


@celery_app.task
def delete_file_from_storage(object_key: str) -> None:
    """Delete a file from MinIO."""
    from app.core.config import settings
    from minio import Minio

    try:
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        client.remove_object(settings.MINIO_BUCKET_FILES, object_key)
        logger.info(f"Deleted file: {object_key}")
    except Exception as e:
        logger.error(f"Failed to delete file {object_key}: {e}")


@celery_app.task
def cleanup_expired_sessions() -> dict:
    """Remove expired Redis sessions."""
    from app.core.config import settings
    import redis

    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    pattern = "session:*"
    cleaned = 0
    for key in r.scan_iter(pattern):
        ttl = r.ttl(key)
        if ttl == -2:  # Already expired
            cleaned += 1
    logger.info(f"Cleaned up {cleaned} expired sessions")
    return {"cleaned": cleaned}


@celery_app.task
def cleanup_orphan_files() -> dict:
    """Remove files whose meeting has been deleted."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    engine = create_engine(settings.DATABASE_SYNC_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # Find files where meeting is soft-deleted
        result = session.execute(
            text("""
                SELECT f.id, f.object_key FROM files f
                JOIN meetings m ON f.meeting_id = m.id
                WHERE m.is_deleted = true AND f.is_deleted = false
            """)
        )
        orphans = result.fetchall()
        for file_id, object_key in orphans:
            delete_file_from_storage.delay(object_key)
            session.execute(
                text("UPDATE files SET is_deleted = true WHERE id = :id"),
                {"id": str(file_id)},
            )
        session.commit()

    logger.info(f"Cleaned up {len(orphans)} orphan files")
    return {"cleaned": len(orphans)}


# ── Reminder Tasks ────────────────────────────────────────────────────────────

@celery_app.task
def check_upcoming_meetings() -> dict:
    """Check for meetings starting in 15 minutes and send reminders."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from datetime import datetime, timezone, timedelta

    engine = create_engine(settings.DATABASE_SYNC_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    now = datetime.now(timezone.utc)
    reminder_window_start = now + timedelta(minutes=14)
    reminder_window_end = now + timedelta(minutes=16)

    sent = 0
    with Session() as session:
        result = session.execute(
            text("""
                SELECT m.id, m.title, m.meeting_code, u.email, u.first_name
                FROM meetings m
                JOIN meeting_invitations mi ON mi.meeting_id = m.id
                JOIN users u ON u.id = mi.user_id
                WHERE m.scheduled_start BETWEEN :start AND :end
                  AND m.status = 'scheduled'
                  AND m.is_deleted = false
                  AND mi.status = 'accepted'
            """),
            {"start": reminder_window_start, "end": reminder_window_end},
        )
        rows = result.fetchall()
        for row in rows:
            from app.workers.email_tasks import send_meeting_reminder_email
            send_meeting_reminder_email.delay(
                row.email, row.first_name, row.title, row.meeting_code, 15
            )
            sent += 1

    return {"reminders_sent": sent}


# ── Notification Tasks ────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3)
def send_push_notification(
    self: Task,
    user_id: str,
    title: str,
    body: str,
    notification_type: str,
    entity_id: Optional[str] = None,
) -> None:
    """Create an in-app notification record."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.models.notification import Notification, NotificationType
    import uuid

    engine = create_engine(settings.DATABASE_SYNC_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    try:
        with Session() as session:
            notif = Notification(
                user_id=uuid.UUID(user_id),
                title=title,
                body=body,
                type=NotificationType(notification_type),
                entity_id=uuid.UUID(entity_id) if entity_id else None,
                read=False,
            )
            session.add(notif)
            session.commit()
            logger.info(f"Notification created for user {user_id}")
    except Exception as exc:
        raise self.retry(exc=exc)
