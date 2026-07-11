"""Enterprise Meet — Meeting ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditableBase

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.participant import Participant
    from app.models.message import Message
    from app.models.recording import Recording
    from app.models.meeting_settings import MeetingSettings
    from app.models.invitation import MeetingInvitation
    from app.models.file import File


class MeetingType(str, enum.Enum):
    INSTANT = "instant"
    SCHEDULED = "scheduled"
    RECURRING = "recurring"
    WEBINAR = "webinar"


class MeetingStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"


class Meeting(AuditableBase):
    """Meeting record tracking lifecycle, settings, and participants."""

    __tablename__ = "meetings"

    # ── Core Fields ───────────────────────────────────────────────────────────
    host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Meeting Code ──────────────────────────────────────────────────────────
    meeting_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    meeting_password: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True  # hashed
    )

    # ── Schedule ──────────────────────────────────────────────────────────────
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scheduled_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Type & Status ─────────────────────────────────────────────────────────
    meeting_type: Mapped[MeetingType] = mapped_column(
        Enum(MeetingType, name="meeting_type", values_callable=lambda x: [e.value for e in x]),
        default=MeetingType.INSTANT,
        nullable=False,
    )
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus, name="meeting_status", values_callable=lambda x: [e.value for e in x]),
        default=MeetingStatus.SCHEDULED,
        nullable=False,
        index=True,
    )

    # ── Feature Flags ─────────────────────────────────────────────────────────
    recording_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    waiting_room: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    host: Mapped["User"] = relationship(
        "User", back_populates="hosted_meetings", foreign_keys=[host_id]
    )
    participants: Mapped[List["Participant"]] = relationship(
        "Participant", back_populates="meeting", cascade="all, delete-orphan"
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="meeting", cascade="all, delete-orphan"
    )
    recordings: Mapped[List["Recording"]] = relationship(
        "Recording", back_populates="meeting", cascade="all, delete-orphan"
    )
    settings: Mapped[Optional["MeetingSettings"]] = relationship(
        "MeetingSettings", back_populates="meeting", uselist=False,
        cascade="all, delete-orphan", lazy="selectin",
    )
    invitations: Mapped[List["MeetingInvitation"]] = relationship(
        "MeetingInvitation", back_populates="meeting", cascade="all, delete-orphan"
    )
    files: Mapped[List["File"]] = relationship(
        "File", back_populates="meeting", cascade="all, delete-orphan"
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_meetings_host_status", "host_id", "status"),
        Index("ix_meetings_code_status", "meeting_code", "status"),
        Index("ix_meetings_scheduled_start", "scheduled_start"),
    )

    @property
    def is_active(self) -> bool:
        return self.status == MeetingStatus.ACTIVE

    @property
    def duration_seconds(self) -> Optional[int]:
        if self.actual_start and self.actual_end:
            return int((self.actual_end - self.actual_start).total_seconds())
        return None
