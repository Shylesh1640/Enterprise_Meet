"""Enterprise Meet — MeetingSettings ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditableBase

if TYPE_CHECKING:
    from app.models.meeting import Meeting


class MeetingSettings(AuditableBase):
    """
    Per-meeting configuration for feature permissions.
    One-to-one with Meeting.
    """

    __tablename__ = "meeting_settings"

    # ── Reference (1:1) ───────────────────────────────────────────────────────
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Permissions ───────────────────────────────────────────────────────────
    allow_chat: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_screen_share: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_recording: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_unmute: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_camera: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    waiting_room: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_reactions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_polls: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_hand_raise: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    mute_on_entry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    video_off_on_entry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Relationship ──────────────────────────────────────────────────────────
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="settings")
