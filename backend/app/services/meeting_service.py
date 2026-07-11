"""Enterprise Meet — Meeting Service: create, join, leave, lock, invite, history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.redis import add_to_meeting_presence, remove_from_meeting_presence
from app.core.security import generate_meeting_code, get_password_hash, verify_password
from app.models.meeting import Meeting, MeetingStatus
from app.models.participant import Participant, ParticipantRole
from app.models.meeting_settings import MeetingSettings
from app.models.invitation import MeetingInvitation, InvitationStatus
from app.models.notification import NotificationType
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.user_repository import UserRepository
from app.repositories.misc_repositories import NotificationRepository
from app.schemas.meeting import (
    CreateMeetingRequest,
    InviteUserRequest,
    JoinMeetingRequest,
    MeetingResponse,
    UpdateMeetingRequest,
)

logger = get_logger(__name__)


class MeetingService:
    """Business logic for meeting lifecycle management."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._meetings = MeetingRepository(db)
        self._participants = ParticipantRepository(db)
        self._users = UserRepository(db)
        self._notifications = NotificationRepository(db)

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_meeting(self, host_id: UUID, payload: CreateMeetingRequest) -> Meeting:
        """Create a new meeting with auto-generated code and default settings."""
        # Generate unique meeting code
        code = generate_meeting_code()
        # Ensure uniqueness (retry up to 5 times)
        for _ in range(5):
            existing = await self._meetings.get_by_code(code)
            if not existing:
                break
            code = generate_meeting_code()

        password_hash = None
        if payload.meeting_password:
            password_hash = get_password_hash(payload.meeting_password)

        meeting_status = (
            MeetingStatus.ACTIVE
            if payload.meeting_type == "instant"
            else MeetingStatus.SCHEDULED
        )

        meeting = await self._meetings.create(
            host_id=host_id,
            title=payload.title,
            description=payload.description,
            meeting_code=code,
            meeting_password=password_hash,
            meeting_type=payload.meeting_type,
            status=meeting_status,
            recording_enabled=payload.recording_enabled,
            waiting_room=payload.waiting_room,
            scheduled_start=payload.scheduled_start,
            scheduled_end=payload.scheduled_end,
            actual_start=datetime.now(timezone.utc) if meeting_status == MeetingStatus.ACTIVE else None,
            locked=False,
            created_by=host_id,
        )

        # Create default settings
        settings_data = payload.settings or {}
        settings_kwargs = {}
        if settings_data:
            settings_kwargs = settings_data.model_dump() if hasattr(settings_data, "model_dump") else dict(settings_data)

        self._db.add(MeetingSettings(meeting_id=meeting.id, **settings_kwargs))
        await self._db.flush()

        # Auto-join host as host participant
        if meeting_status == MeetingStatus.ACTIVE:
            await self._join_as_host(meeting.id, host_id)

        logger.info("meeting_created", meeting_id=str(meeting.id), host_id=str(host_id))
        return meeting

    # ── Get / List ────────────────────────────────────────────────────────────

    async def get_meeting(self, meeting_id: UUID, user_id: UUID) -> Meeting:
        meeting = await self._meetings.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
        return meeting

    async def get_meeting_by_code(self, code: str) -> Meeting:
        meeting = await self._meetings.get_by_code(code)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
        return meeting

    async def list_meetings(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        meeting_status: Optional[str] = None,
    ) -> Tuple[List[Meeting], int]:
        return await self._meetings.get_meetings_for_host(
            user_id, page=page, page_size=page_size, status=meeting_status
        )

    async def get_history(
        self, user_id: UUID, *, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Meeting], int]:
        return await self._meetings.get_history_for_user(user_id, page=page, page_size=page_size)

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_meeting(
        self, meeting_id: UUID, host_id: UUID, payload: UpdateMeetingRequest
    ) -> Meeting:
        meeting = await self._require_meeting(meeting_id)
        self._require_host(meeting, host_id)

        update_data = {k: v for k, v in payload.model_dump(exclude_unset=True, exclude={"settings"}).items() if v is not None}
        update_data["updated_by"] = host_id
        if update_data:
            await self._meetings.update(meeting_id, **update_data)

        if payload.settings:
            from sqlalchemy import select
            from app.models.meeting_settings import MeetingSettings
            result = await self._db.execute(
                select(MeetingSettings).where(MeetingSettings.meeting_id == meeting_id)
            )
            ms = result.scalar_one_or_none()
            if ms:
                for k, v in payload.settings.model_dump(exclude_unset=True).items():
                    setattr(ms, k, v)
                await self._db.flush()

        await self._db.refresh(meeting)
        return meeting

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete_meeting(self, meeting_id: UUID, host_id: UUID) -> None:
        meeting = await self._require_meeting(meeting_id)
        self._require_host(meeting, host_id)
        await self._meetings.delete(meeting_id, deleted_by=host_id)
        logger.info("meeting_deleted", meeting_id=str(meeting_id), host_id=str(host_id))

    # ── Join ──────────────────────────────────────────────────────────────────

    async def join_meeting(
        self, meeting_id: UUID, user_id: UUID, payload: JoinMeetingRequest
    ) -> Participant:
        meeting = await self._require_meeting(meeting_id)

        if meeting.locked and meeting.host_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Meeting is locked by the host",
            )

        if meeting.status == MeetingStatus.ENDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This meeting has ended",
            )

        if meeting.status == MeetingStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This meeting has been cancelled",
            )

        # Password check
        if meeting.meeting_password:
            if not payload.meeting_password:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Meeting password required",
                )
            if not verify_password(payload.meeting_password, meeting.meeting_password):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Incorrect meeting password",
                )

        # Check for existing active participant record
        existing = await self._participants.get_by_meeting_and_user(meeting_id, user_id)
        if existing and existing.left_at is None:
            return existing  # Already joined

        # Activate meeting if scheduled
        if meeting.status == MeetingStatus.SCHEDULED:
            meeting.status = MeetingStatus.ACTIVE
            meeting.actual_start = datetime.now(timezone.utc)
            await self._db.flush()

        role = ParticipantRole.HOST if meeting.host_id == user_id else ParticipantRole.ATTENDEE

        participant = await self._participants.create(
            meeting_id=meeting_id,
            user_id=user_id,
            role=role,
            joined_at=datetime.now(timezone.utc),
            mic_enabled=False,
            camera_enabled=False,
            screen_sharing=False,
            hand_raised=False,
            connection_status="connected",
        )

        await add_to_meeting_presence(str(meeting_id), str(user_id))
        logger.info("participant_joined", meeting_id=str(meeting_id), user_id=str(user_id))
        return participant

    # ── Leave ─────────────────────────────────────────────────────────────────

    async def leave_meeting(self, meeting_id: UUID, user_id: UUID) -> None:
        participant = await self._participants.get_by_meeting_and_user(meeting_id, user_id)
        if participant and participant.left_at is None:
            await self._participants.mark_left(participant.id)

        await remove_from_meeting_presence(str(meeting_id), str(user_id))

        # If host left, check if anyone remains; if not, end the meeting
        meeting = await self._meetings.get_by_id(meeting_id)
        if meeting and meeting.host_id == user_id:
            remaining = await self._participants.count_active(meeting_id)
            if remaining == 0:
                meeting.status = MeetingStatus.ENDED
                meeting.actual_end = datetime.now(timezone.utc)
                await self._db.flush()

        logger.info("participant_left", meeting_id=str(meeting_id), user_id=str(user_id))

    # ── Lock / Unlock ─────────────────────────────────────────────────────────

    async def lock_meeting(self, meeting_id: UUID, host_id: UUID) -> Meeting:
        meeting = await self._require_meeting(meeting_id)
        self._require_host(meeting, host_id)
        await self._meetings.update(meeting_id, locked=True)
        await self._db.refresh(meeting)
        return meeting

    async def unlock_meeting(self, meeting_id: UUID, host_id: UUID) -> Meeting:
        meeting = await self._require_meeting(meeting_id)
        self._require_host(meeting, host_id)
        await self._meetings.update(meeting_id, locked=False)
        await self._db.refresh(meeting)
        return meeting

    # ── Invite ────────────────────────────────────────────────────────────────

    async def invite_users(
        self, meeting_id: UUID, inviter_id: UUID, payload: InviteUserRequest
    ) -> dict:
        meeting = await self._require_meeting(meeting_id)
        invited = 0

        if payload.user_ids:
            for uid in payload.user_ids:
                from sqlalchemy import select
                from app.models.invitation import MeetingInvitation
                # Check for existing invite
                result = await self._db.execute(
                    select(MeetingInvitation).where(
                        MeetingInvitation.meeting_id == meeting_id,
                        MeetingInvitation.user_id == uid,
                    )
                )
                existing = result.scalar_one_or_none()
                if not existing:
                    inv = MeetingInvitation(
                        meeting_id=meeting_id,
                        user_id=uid,
                        invited_by=inviter_id,
                        status=InvitationStatus.PENDING,
                        invited_at=datetime.now(timezone.utc),
                    )
                    self._db.add(inv)
                    # Send notification
                    await self._notifications.create(
                        user_id=uid,
                        title="Meeting Invitation",
                        body=f"You've been invited to {meeting.title}",
                        type=NotificationType.MEETING_INVITE,
                        entity_id=meeting_id,
                    )
                    invited += 1

        if payload.emails:
            from app.workers.email_tasks import send_meeting_invitation_email
            for email in payload.emails:
                try:
                    send_meeting_invitation_email.delay(email, meeting.title, meeting.meeting_code)
                    invited += 1
                except Exception as e:
                    logger.error("invite_email_failed", email=email, error=str(e))

        await self._db.flush()
        return {"invited": invited}

    # ── Internal Helpers ──────────────────────────────────────────────────────

    async def _require_meeting(self, meeting_id: UUID) -> Meeting:
        meeting = await self._meetings.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
        return meeting

    def _require_host(self, meeting: Meeting, user_id: UUID) -> None:
        if meeting.host_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the host can perform this action",
            )

    async def _join_as_host(self, meeting_id: UUID, host_id: UUID) -> Participant:
        return await self._participants.create(
            meeting_id=meeting_id,
            user_id=host_id,
            role=ParticipantRole.HOST,
            joined_at=datetime.now(timezone.utc),
            mic_enabled=False,
            camera_enabled=False,
            screen_sharing=False,
            hand_raised=False,
            connection_status="connected",
        )
