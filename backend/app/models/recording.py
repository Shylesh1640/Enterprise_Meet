"""Enterprise Meet — Recording ORM model."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditableBase

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.user import User


class RecordingStatus(str, enum.Enum):
    RECORDING = "recording"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Recording(AuditableBase):
    """Meeting recording stored in object storage."""

    __tablename__ = "recordings"

    # ── References ────────────────────────────────────────────────────────────
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Storage ───────────────────────────────────────────────────────────────
    file_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    object_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # MinIO key

    # ── Metadata ──────────────────────────────────────────────────────────────
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # seconds
    size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)   # bytes
    status: Mapped[RecordingStatus] = mapped_column(
        Enum(RecordingStatus, name="recording_status", values_callable=lambda x: [e.value for e in x]),
        default=RecordingStatus.RECORDING,
        nullable=False,
    )
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="recordings")
    started_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[started_by]
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_recordings_meeting_created", "meeting_id", "created_at"),
        Index("ix_recordings_status", "status"),
    )
