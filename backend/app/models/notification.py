"""Enterprise Meet — Notification ORM model."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditableBase

if TYPE_CHECKING:
    from app.models.user import User


class NotificationType(str, enum.Enum):
    MEETING_INVITE = "meeting_invite"
    MEETING_STARTED = "meeting_started"
    MEETING_ENDED = "meeting_ended"
    MEETING_REMINDER = "meeting_reminder"
    RECORDING_READY = "recording_ready"
    SYSTEM = "system"
    CHAT_MENTION = "chat_mention"


class Notification(AuditableBase):
    """User notification with type, read status, and optional action data."""

    __tablename__ = "notifications"

    # ── Reference ─────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Content ───────────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )

    # ── State ─────────────────────────────────────────────────────────────────
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Optional action link ──────────────────────────────────────────────────
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="notifications")

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "read"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_type", "type"),
    )
