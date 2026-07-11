"""Enterprise Meet — Message Repository."""

from __future__ import annotations

from typing import List, Tuple
from uuid import UUID

from sqlalchemy import func, select

from app.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    model = Message

    async def get_meeting_messages(
        self,
        meeting_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
        include_deleted: bool = False,
    ) -> Tuple[List[Message], int]:
        stmt = select(Message).where(Message.meeting_id == meeting_id)
        count_stmt = select(func.count()).select_from(Message).where(
            Message.meeting_id == meeting_id
        )
        if not include_deleted:
            stmt = stmt.where(Message.deleted.is_(False))
            count_stmt = count_stmt.where(Message.deleted.is_(False))

        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(Message.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def soft_delete_message(self, message_id: UUID, deleted_by: UUID) -> Optional[Message]:
        msg = await self.get_by_id(message_id)
        if msg:
            msg.deleted = True
            msg.updated_by = deleted_by
            await self._session.flush()
        return msg
