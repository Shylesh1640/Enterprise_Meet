"""Enterprise Meet — User ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditableBase

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.notification import Notification
    from app.models.participant import Participant
    from app.models.audit_log import AuditLog


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    ADMIN = "admin"


class ThemePreference(str, enum.Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class User(AuditableBase):
    """User account with full profile, preferences, and auth columns."""

    __tablename__ = "users"

    # ── Identity ──────────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(50), unique=True, nullable=True, index=True
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True  # nullable for future OAuth
    )

    # ── Profile ───────────────────────────────────────────────────────────────
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Preferences ───────────────────────────────────────────────────────────
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    theme: Mapped[ThemePreference] = mapped_column(
        Enum(ThemePreference, name="theme_preference", values_callable=lambda x: [e.value for e in x]),
        default=ThemePreference.SYSTEM,
        nullable=False,
    )

    # ── Status & Auth ─────────────────────────────────────────────────────────
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", values_callable=lambda x: [e.value for e in x]),
        default=UserStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Verification tokens (hashed, stored transiently) ─────────────────────
    email_verify_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    password_reset_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    hosted_meetings: Mapped[List["Meeting"]] = relationship(
        "Meeting", back_populates="host", foreign_keys="Meeting.host_id"
    )
    participations: Mapped[List["Participant"]] = relationship(
        "Participant", back_populates="user"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", back_populates="user"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_users_email_verified", "email", "email_verified"),
        Index("ix_users_status_created", "status", "created_at"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
