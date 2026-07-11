"""Enterprise Meet — Message ORM model (meeting chat)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditableBase

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.user import User


class Message(AuditableBase):
    """Chat message within a meeting, with edit/delete/reply support."""

    __tablename__ = "messages"

    # ── References ────────────────────────────────────────────────────────────
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # preserve history if user deleted
        index=True,
    )

    # ── Content ───────────────────────────────────────────────────────────────
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # ── State ─────────────────────────────────────────────────────────────────
    edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Threading ─────────────────────────────────────────────────────────────
    reply_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="messages")
    sender: Mapped[Optional["User"]] = relationship("User", foreign_keys=[sender_id])
    parent: Mapped[Optional["Message"]] = relationship(
        "Message", remote_side="Message.id", foreign_keys=[reply_to]
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_messages_meeting_created", "meeting_id", "created_at"),
        Index("ix_messages_sender_meeting", "sender_id", "meeting_id"),
    )
