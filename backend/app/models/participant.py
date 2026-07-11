"""Enterprise Meet — Participant ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditableBase

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.user import User


class ParticipantRole(str, enum.Enum):
    HOST = "host"
    CO_HOST = "co_host"
    PRESENTER = "presenter"
    ATTENDEE = "attendee"


class ConnectionStatus(str, enum.Enum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"


class Participant(AuditableBase):
    """Tracks a user's presence and state within a specific meeting."""

    __tablename__ = "participants"

    # ── References ────────────────────────────────────────────────────────────
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Role ──────────────────────────────────────────────────────────────────
    role: Mapped[ParticipantRole] = mapped_column(
        Enum(ParticipantRole, name="participant_role", values_callable=lambda x: [e.value for e in x]),
        default=ParticipantRole.ATTENDEE,
        nullable=False,
    )

    # ── Timing ────────────────────────────────────────────────────────────────
    joined_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    left_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Media State ───────────────────────────────────────────────────────────
    mic_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    camera_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    screen_sharing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hand_raised: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Connection ────────────────────────────────────────────────────────────
    connection_status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus, name="connection_status", values_callable=lambda x: [e.value for e in x]),
        default=ConnectionStatus.CONNECTING,
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="participants")
    user: Mapped["User"] = relationship("User", back_populates="participations")

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_participants_meeting_user", "meeting_id", "user_id"),
        Index("ix_participants_meeting_role", "meeting_id", "role"),
        Index("ix_participants_user_joined", "user_id", "joined_at"),
    )

    @property
    def is_active(self) -> bool:
        return self.joined_at is not None and self.left_at is None

    @property
    def duration_seconds(self) -> Optional[int]:
        if self.joined_at and self.left_at:
            return int((self.left_at - self.joined_at).total_seconds())
        return None
