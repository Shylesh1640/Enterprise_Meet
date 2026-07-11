"""Enterprise Meet — Notification, Recording, File, AuditLog repositories."""

from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select, update

from app.models.notification import Notification
from app.models.recording import Recording
from app.models.file import File
from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


# ── Notification Repository ───────────────────────────────────────────────────

class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def get_user_notifications(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> Tuple[List[Notification], int]:
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_deleted.is_(False),
        )
        count_stmt = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.is_deleted.is_(False),
        )
        if unread_only:
            stmt = stmt.where(Notification.read.is_(False))
            count_stmt = count_stmt.where(Notification.read.is_(False))

        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def mark_read(self, user_id: UUID, notification_ids: Optional[List[UUID]] = None) -> int:
        """Mark notifications as read. If no IDs given, mark all for user."""
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read.is_(False),
                Notification.is_deleted.is_(False),
            )
            .values(read=True)
        )
        if notification_ids:
            stmt = stmt.where(Notification.id.in_(notification_ids))
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def count_unread(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.read.is_(False),
            Notification.is_deleted.is_(False),
        )
        return (await self._session.execute(stmt)).scalar_one()


# ── Recording Repository ──────────────────────────────────────────────────────

class RecordingRepository(BaseRepository[Recording]):
    model = Recording

    async def get_meeting_recordings(
        self,
        meeting_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Recording], int]:
        stmt = select(Recording).where(
            Recording.meeting_id == meeting_id,
            Recording.is_deleted.is_(False),
        )
        count_stmt = select(func.count()).select_from(Recording).where(
            Recording.meeting_id == meeting_id,
            Recording.is_deleted.is_(False),
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(Recording.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_active_recording(self, meeting_id: UUID) -> Optional[Recording]:
        from app.models.recording import RecordingStatus
        stmt = select(Recording).where(
            Recording.meeting_id == meeting_id,
            Recording.status == RecordingStatus.RECORDING,
            Recording.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_total_size(self) -> int:
        from sqlalchemy import coalesce
        result = await self._session.execute(
            select(coalesce(func.sum(Recording.size), 0)).where(
                Recording.is_deleted.is_(False)
            )
        )
        return result.scalar_one()


# ── File Repository ───────────────────────────────────────────────────────────

class FileRepository(BaseRepository[File]):
    model = File

    async def get_meeting_files(
        self,
        meeting_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[File], int]:
        stmt = select(File).where(
            File.meeting_id == meeting_id,
            File.is_deleted.is_(False),
        )
        count_stmt = select(func.count()).select_from(File).where(
            File.meeting_id == meeting_id,
            File.is_deleted.is_(False),
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(File.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_total_size(self) -> int:
        from sqlalchemy import coalesce
        result = await self._session.execute(
            select(coalesce(func.sum(File.size), 0)).where(File.is_deleted.is_(False))
        )
        return result.scalar_one()


# ── AuditLog Repository ───────────────────────────────────────────────────────

class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def log(
        self,
        *,
        user_id: Optional[UUID] = None,
        action: str,
        entity: str,
        entity_id: Optional[UUID] = None,
        ip: Optional[str] = None,
        device: Optional[str] = None,
        user_agent: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        extra: Optional[str] = None,
    ) -> AuditLog:
        return await self.create(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            ip=ip,
            device=device,
            user_agent=user_agent,
            old_value=old_value,
            new_value=new_value,
            extra=extra,
        )

    async def get_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        entity: Optional[str] = None,
    ) -> Tuple[List[AuditLog], int]:
        stmt = select(AuditLog)
        count_stmt = select(func.count()).select_from(AuditLog)

        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
            count_stmt = count_stmt.where(AuditLog.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
            count_stmt = count_stmt.where(AuditLog.action == action)
        if entity:
            stmt = stmt.where(AuditLog.entity == entity)
            count_stmt = count_stmt.where(AuditLog.entity == entity)

        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total
