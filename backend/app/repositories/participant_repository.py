"""Enterprise Meet — Participant, Message, Recording, Notification, File repositories."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select, update

from app.models.participant import Participant, ParticipantRole
from app.repositories.base import BaseRepository


class ParticipantRepository(BaseRepository[Participant]):
    model = Participant

    async def get_by_meeting_and_user(
        self, meeting_id: UUID, user_id: UUID
    ) -> Optional[Participant]:
        stmt = select(Participant).where(
            Participant.meeting_id == meeting_id,
            Participant.user_id == user_id,
            Participant.is_deleted.is_(False),
        ).order_by(Participant.joined_at.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_participants(self, meeting_id: UUID) -> List[Participant]:
        stmt = select(Participant).where(
            Participant.meeting_id == meeting_id,
            Participant.joined_at.is_not(None),
            Participant.left_at.is_(None),
            Participant.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_active(self, meeting_id: UUID) -> int:
        stmt = select(func.count()).select_from(Participant).where(
            Participant.meeting_id == meeting_id,
            Participant.joined_at.is_not(None),
            Participant.left_at.is_(None),
            Participant.is_deleted.is_(False),
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def mark_left(self, participant_id: UUID) -> None:
        await self._session.execute(
            update(Participant)
            .where(Participant.id == participant_id)
            .values(left_at=datetime.now(timezone.utc))
        )
        await self._session.flush()
