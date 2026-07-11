"""Enterprise Meet — File ORM model (uploaded to MinIO)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditableBase

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.user import User


class File(AuditableBase):
    """Uploaded file associated with a meeting, stored in MinIO."""

    __tablename__ = "files"

    # ── References ────────────────────────────────────────────────────────────
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── File Metadata ─────────────────────────────────────────────────────────
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)  # MinIO key
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)  # bytes

    # ── Relationships ─────────────────────────────────────────────────────────
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="files")
    uploader: Mapped[Optional["User"]] = relationship("User", foreign_keys=[uploaded_by])

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_files_meeting_created", "meeting_id", "created_at"),
        Index("ix_files_uploader", "uploaded_by"),
    )

    @property
    def size_mb(self) -> float:
        return round(self.size / (1024 * 1024), 2)
