"""Enterprise Meet — Generic async repository base with CRUD, soft delete, pagination."""

from __future__ import annotations

from typing import Any, Generic, List, Optional, Tuple, Type, TypeVar
from uuid import UUID

from sqlalchemy import Select, asc, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import AuditableBase

ModelT = TypeVar("ModelT", bound=AuditableBase)


class BaseRepository(Generic[ModelT]):
    """
    Generic async repository providing:
    - get_by_id / get_all / paginate
    - create / update / delete (soft)
    - count / exists
    Concrete repos subclass this and add domain-specific queries.
    """

    model: Type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, id: UUID, *, include_deleted: bool = False) -> Optional[ModelT]:
        stmt = select(self.model).where(self.model.id == id)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted.is_(False))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        order_by: Optional[str] = "created_at",
        order_dir: str = "desc",
        include_deleted: bool = False,
    ) -> List[ModelT]:
        stmt = select(self.model)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted.is_(False))
        stmt = self._apply_order(stmt, order_by, order_dir)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def paginate(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        order_by: Optional[str] = "created_at",
        order_dir: str = "desc",
        include_deleted: bool = False,
        filters: Optional[dict[str, Any]] = None,
    ) -> Tuple[List[ModelT], int]:
        """Return (items, total_count) for the given page."""
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted.is_(False))
            count_stmt = count_stmt.where(self.model.is_deleted.is_(False))

        if filters:
            for column_name, value in filters.items():
                column = getattr(self.model, column_name, None)
                if column is not None and value is not None:
                    stmt = stmt.where(column == value)
                    count_stmt = count_stmt.where(column == value)

        total_result = await self._session.execute(count_stmt)
        total: int = total_result.scalar_one()

        stmt = self._apply_order(stmt, order_by, order_dir)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def count(self, *, include_deleted: bool = False) -> int:
        stmt = select(func.count()).select_from(self.model)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted.is_(False))
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def exists(self, id: UUID) -> bool:
        stmt = select(func.count()).select_from(self.model).where(
            self.model.id == id, self.model.is_deleted.is_(False)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create(self, **kwargs: Any) -> ModelT:
        """Create and persist a new model instance."""
        instance = self.model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(self, id: UUID, **kwargs: Any) -> Optional[ModelT]:
        """Update specific fields of a model by ID."""
        stmt = (
            update(self.model)
            .where(self.model.id == id, self.model.is_deleted.is_(False))
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none()

    async def save(self, instance: ModelT) -> ModelT:
        """Merge an existing detached instance or flush a tracked one."""
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, id: UUID, deleted_by: Optional[UUID] = None) -> bool:
        """Soft delete a record by ID."""
        instance = await self.get_by_id(id)
        if not instance:
            return False
        instance.soft_delete(deleted_by)
        await self._session.flush()
        return True

    async def hard_delete(self, id: UUID) -> bool:
        """Permanently remove a record (use sparingly)."""
        instance = await self.get_by_id(id, include_deleted=True)
        if not instance:
            return False
        await self._session.delete(instance)
        await self._session.flush()
        return True

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _apply_order(self, stmt: Select, order_by: Optional[str], order_dir: str) -> Select:
        if order_by:
            column = getattr(self.model, order_by, None)
            if column is not None:
                stmt = stmt.order_by(desc(column) if order_dir == "desc" else asc(column))
        return stmt
