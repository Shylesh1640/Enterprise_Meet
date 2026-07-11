"""Enterprise Meet — Meeting Repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select

from app.models.meeting import Meeting, MeetingStatus
from app.repositories.base import BaseRepository


class MeetingRepository(BaseRepository[Meeting]):
    model = Meeting

    async def get_by_code(self, meeting_code: str) -> Optional[Meeting]:
        stmt = select(Meeting).where(
            Meeting.meeting_code == meeting_code.lower(),
            Meeting.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_code(self, meeting_code: str) -> Optional[Meeting]:
        stmt = select(Meeting).where(
            Meeting.meeting_code == meeting_code.lower(),
            Meeting.status == MeetingStatus.ACTIVE,
            Meeting.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_meetings_for_host(
        self,
        host_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Tuple[List[Meeting], int]:
        stmt = select(Meeting).where(
            Meeting.host_id == host_id,
            Meeting.is_deleted.is_(False),
        )
        count_stmt = select(func.count()).select_from(Meeting).where(
            Meeting.host_id == host_id,
            Meeting.is_deleted.is_(False),
        )
        if status:
            stmt = stmt.where(Meeting.status == status)
            count_stmt = count_stmt.where(Meeting.status == status)

        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(Meeting.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_history_for_user(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Meeting], int]:
        """Meetings the user participated in (as host or attendee)."""
        from app.models.participant import Participant

        stmt = (
            select(Meeting)
            .join(Participant, Participant.meeting_id == Meeting.id)
            .where(
                Participant.user_id == user_id,
                Participant.left_at.is_not(None),
                Meeting.is_deleted.is_(False),
            )
            .distinct()
        )
        count_stmt = (
            select(func.count())
            .select_from(Meeting)
            .join(Participant, Participant.meeting_id == Meeting.id)
            .where(
                Participant.user_id == user_id,
                Participant.left_at.is_not(None),
                Meeting.is_deleted.is_(False),
            )
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(Meeting.actual_start.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_active_meetings(self) -> List[Meeting]:
        stmt = select(Meeting).where(
            Meeting.status == MeetingStatus.ACTIVE,
            Meeting.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_status(self) -> dict[str, int]:
        result = await self._session.execute(
            select(Meeting.status, func.count(Meeting.id))
            .where(Meeting.is_deleted.is_(False))
            .group_by(Meeting.status)
        )
        return {str(row[0].value): row[1] for row in result.all()}
