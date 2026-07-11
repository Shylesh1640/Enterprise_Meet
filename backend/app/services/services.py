"""Enterprise Meet — User, Chat, Recording, File, Notification services."""

from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.user import User
from app.models.message import Message
from app.models.recording import Recording, RecordingStatus
from app.models.file import File
from app.models.notification import Notification
from app.repositories.user_repository import UserRepository
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.misc_repositories import (
    RecordingRepository,
    FileRepository,
    NotificationRepository,
)
from app.schemas.user import UpdateProfileRequest
from app.schemas.responses import (
    SendMessageRequest,
    EditMessageRequest,
    StartRecordingRequest,
    MarkNotificationsReadRequest,
)

logger = get_logger(__name__)


# ── User Service ──────────────────────────────────────────────────────────────

class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self._users = UserRepository(db)
        self._db = db

    async def get_user(self, user_id: UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def update_profile(self, user: User, payload: UpdateProfileRequest) -> User:
        update_data = payload.model_dump(exclude_unset=True, exclude_none=True)

        if "username" in update_data:
            exists = await self._users.username_exists(update_data["username"], exclude_id=user.id)
            if exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already taken",
                )

        for k, v in update_data.items():
            setattr(user, k, v)
        user.updated_by = user.id
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def update_avatar(self, user: User, avatar_url: str) -> User:
        user.avatar = avatar_url
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def delete_account(self, user: User) -> None:
        user.soft_delete(user.id)
        await self._db.flush()
        logger.info("account_deleted", user_id=str(user.id))

    async def search_users(
        self, query: str, *, page: int = 1, page_size: int = 20
    ) -> Tuple[List[User], int]:
        return await self._users.search(query, page=page, page_size=page_size)

    async def list_users(
        self, *, page: int = 1, page_size: int = 20
    ) -> Tuple[List[User], int]:
        return await self._users.paginate(page=page, page_size=page_size)


# ── Chat Service ──────────────────────────────────────────────────────────────

class ChatService:
    def __init__(self, db: AsyncSession) -> None:
        self._messages = MessageRepository(db)
        self._meetings = MeetingRepository(db)
        self._participants = ParticipantRepository(db)
        self._db = db

    async def get_messages(
        self,
        meeting_id: UUID,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Message], int]:
        # Verify participant
        await self._require_participant(meeting_id, user_id)
        return await self._messages.get_meeting_messages(
            meeting_id, page=page, page_size=page_size
        )

    async def send_message(
        self, user_id: UUID, payload: SendMessageRequest
    ) -> Message:
        await self._require_participant(payload.meeting_id, user_id)
        msg = await self._messages.create(
            meeting_id=payload.meeting_id,
            sender_id=user_id,
            message=payload.message,
            reply_to=payload.reply_to,
            edited=False,
            deleted=False,
            created_by=user_id,
        )
        logger.info("message_sent", meeting_id=str(payload.meeting_id), sender_id=str(user_id))
        return msg

    async def edit_message(
        self, message_id: UUID, user_id: UUID, payload: EditMessageRequest
    ) -> Message:
        msg = await self._messages.get_by_id(message_id)
        if not msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        if msg.sender_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Can only edit your own messages"
            )
        msg.message = payload.message
        msg.edited = True
        msg.updated_by = user_id
        await self._db.flush()
        await self._db.refresh(msg)
        return msg

    async def delete_message(self, message_id: UUID, user_id: UUID) -> None:
        msg = await self._messages.get_by_id(message_id)
        if not msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        if msg.sender_id != user_id:
            # Check if host
            participant = await self._participants.get_by_meeting_and_user(msg.meeting_id, user_id)
            if not participant or participant.role.value not in ("host", "co_host"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
                )
        await self._messages.soft_delete_message(message_id, user_id)

    async def _require_participant(self, meeting_id: UUID, user_id: UUID) -> None:
        p = await self._participants.get_by_meeting_and_user(meeting_id, user_id)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a participant of this meeting",
            )


# ── Recording Service ─────────────────────────────────────────────────────────

class RecordingService:
    def __init__(self, db: AsyncSession) -> None:
        self._recordings = RecordingRepository(db)
        self._meetings = MeetingRepository(db)
        self._db = db

    async def start_recording(self, meeting_id: UUID, user_id: UUID) -> Recording:
        meeting = await self._meetings.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
        if meeting.host_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only host can start recording"
            )

        active = await self._recordings.get_active_recording(meeting_id)
        if active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Recording already in progress"
            )

        recording = await self._recordings.create(
            meeting_id=meeting_id,
            started_by=user_id,
            status=RecordingStatus.RECORDING,
            created_by=user_id,
        )
        logger.info("recording_started", meeting_id=str(meeting_id), recording_id=str(recording.id))
        return recording

    async def stop_recording(self, meeting_id: UUID, recording_id: UUID, user_id: UUID) -> Recording:
        recording = await self._recordings.get_by_id(recording_id)
        if not recording:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")

        recording.status = RecordingStatus.PROCESSING
        await self._db.flush()

        # Dispatch Celery task to finalize the recording
        try:
            from app.workers.recording_tasks import finalize_recording
            finalize_recording.delay(str(recording_id), str(meeting_id))
        except Exception as e:
            logger.error("finalize_recording_task_failed", error=str(e))

        return recording

    async def list_recordings(
        self, meeting_id: UUID, *, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Recording], int]:
        return await self._recordings.get_meeting_recordings(meeting_id, page=page, page_size=page_size)

    async def get_recording(self, recording_id: UUID, user_id: UUID) -> Recording:
        r = await self._recordings.get_by_id(recording_id)
        if not r:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")
        return r

    async def delete_recording(self, recording_id: UUID, user_id: UUID) -> None:
        r = await self._recordings.get_by_id(recording_id)
        if not r:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")

        # Queue deletion from object storage
        try:
            from app.workers.cleanup_tasks import delete_recording_file
            if r.object_key:
                delete_recording_file.delay(r.object_key)
        except Exception as e:
            logger.error("delete_recording_task_failed", error=str(e))

        await self._recordings.delete(recording_id, deleted_by=user_id)


# ── Notification Service ──────────────────────────────────────────────────────

class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self._notifs = NotificationRepository(db)

    async def list_notifications(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> Tuple[List[Notification], int]:
        return await self._notifs.get_user_notifications(
            user_id, page=page, page_size=page_size, unread_only=unread_only
        )

    async def mark_read(self, user_id: UUID, payload: MarkNotificationsReadRequest) -> int:
        return await self._notifs.mark_read(user_id, payload.notification_ids)

    async def delete_notifications(self, user_id: UUID) -> int:
        from sqlalchemy import update
        from app.models.notification import Notification
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_deleted.is_(False),
            )
            .values(is_deleted=True)
        )
        result = await self._notifs._session.execute(stmt)
        await self._notifs._session.flush()
        return result.rowcount


# ── File Service ──────────────────────────────────────────────────────────────

class FileService:
    def __init__(self, db: AsyncSession) -> None:
        self._files = FileRepository(db)
        self._meetings = MeetingRepository(db)

    async def upload_file(
        self,
        meeting_id: UUID,
        user_id: UUID,
        file: UploadFile,
    ) -> File:
        from app.utils.storage import upload_to_minio

        content = await file.read()
        size = len(content)
        object_key, file_url = await upload_to_minio(
            content,
            filename=file.filename or "unnamed",
            content_type=file.content_type or "application/octet-stream",
            bucket="meet-files",
            prefix=f"meetings/{meeting_id}/",
        )

        db_file = await self._files.create(
            meeting_id=meeting_id,
            uploaded_by=user_id,
            filename=object_key.split("/")[-1],
            original_filename=file.filename or "unnamed",
            file_url=file_url,
            object_key=object_key,
            mime_type=file.content_type or "application/octet-stream",
            size=size,
            created_by=user_id,
        )
        logger.info("file_uploaded", file_id=str(db_file.id), size=size)
        return db_file

    async def list_files(
        self, meeting_id: UUID, *, page: int = 1, page_size: int = 20
    ) -> Tuple[List[File], int]:
        return await self._files.get_meeting_files(meeting_id, page=page, page_size=page_size)

    async def delete_file(self, file_id: UUID, user_id: UUID) -> None:
        f = await self._files.get_by_id(file_id)
        if not f:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        if f.uploaded_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete another user's file"
            )
        try:
            from app.workers.cleanup_tasks import delete_file_from_storage
            delete_file_from_storage.delay(f.object_key)
        except Exception as e:
            logger.error("delete_file_task_failed", error=str(e))
        await self._files.delete(file_id, deleted_by=user_id)
