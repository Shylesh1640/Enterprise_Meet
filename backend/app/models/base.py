"""Enterprise Meet — SQLAlchemy declarative base with full audit columns and soft delete."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditableBase(Base):
    """
    Abstract base for all ORM models.
    Provides: UUID PK, timestamps, soft-delete, and audit trail columns.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    def soft_delete(self, deleted_by: Optional[uuid.UUID] = None) -> None:
        """Mark record as deleted without removing from database."""
        from datetime import timezone
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        if deleted_by:
            self.updated_by = deleted_by

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"
