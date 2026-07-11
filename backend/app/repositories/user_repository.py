"""Enterprise Meet — User Repository."""

from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(
            func.lower(User.email) == email.lower(),
            User.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(
            func.lower(User.username) == username.lower(),
            User.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_verify_token(self, token: str) -> Optional[User]:
        stmt = select(User).where(
            User.email_verify_token == token,
            User.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_reset_token(self, token: str) -> Optional[User]:
        stmt = select(User).where(
            User.password_reset_token == token,
            User.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        stmt = select(func.count()).select_from(User).where(
            func.lower(User.email) == email.lower(),
            User.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    async def username_exists(self, username: str, exclude_id: Optional[UUID] = None) -> bool:
        stmt = select(func.count()).select_from(User).where(
            func.lower(User.username) == username.lower(),
            User.is_deleted.is_(False),
        )
        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    async def search(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 20,
        exclude_ids: Optional[List[UUID]] = None,
    ) -> Tuple[List[User], int]:
        """Search users by name or email (partial, case-insensitive)."""
        pattern = f"%{query.lower()}%"
        base_filter = or_(
            func.lower(User.first_name).like(pattern),
            func.lower(User.last_name).like(pattern),
            func.lower(User.email).like(pattern),
            func.lower(func.concat(User.first_name, " ", User.last_name)).like(pattern),
        )
        stmt = select(User).where(
            User.is_deleted.is_(False),
            base_filter,
        )
        count_stmt = select(func.count()).select_from(User).where(
            User.is_deleted.is_(False), base_filter
        )
        if exclude_ids:
            stmt = stmt.where(User.id.not_in(exclude_ids))
            count_stmt = count_stmt.where(User.id.not_in(exclude_ids))

        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(User.first_name, User.last_name)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def count_by_status(self) -> dict[str, int]:
        from sqlalchemy import case
        result = await self._session.execute(
            select(User.status, func.count(User.id))
            .where(User.is_deleted.is_(False))
            .group_by(User.status)
        )
        return {str(row[0].value): row[1] for row in result.all()}
