"""Enterprise Meet — User Pydantic schemas."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """Full user profile response."""

    id: UUID
    email: str
    username: Optional[str] = None
    first_name: str
    last_name: str
    full_name: str
    avatar: Optional[str] = None
    bio: Optional[str] = None
    timezone: str
    language: str
    theme: str
    status: str
    email_verified: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, user: object) -> "UserResponse":
        return cls(
            id=user.id,  # type: ignore[attr-defined]
            email=user.email,  # type: ignore[attr-defined]
            username=user.username,  # type: ignore[attr-defined]
            first_name=user.first_name,  # type: ignore[attr-defined]
            last_name=user.last_name,  # type: ignore[attr-defined]
            full_name=user.full_name,  # type: ignore[attr-defined]
            avatar=user.avatar,  # type: ignore[attr-defined]
            bio=user.bio,  # type: ignore[attr-defined]
            timezone=user.timezone,  # type: ignore[attr-defined]
            language=user.language,  # type: ignore[attr-defined]
            theme=user.theme.value if hasattr(user.theme, "value") else user.theme,  # type: ignore[attr-defined]
            status=user.status.value if hasattr(user.status, "value") else user.status,  # type: ignore[attr-defined]
            email_verified=user.email_verified,  # type: ignore[attr-defined]
        )


class UserPublicResponse(BaseModel):
    """Public profile (limited fields for non-admin requests)."""

    id: UUID
    first_name: str
    last_name: str
    full_name: str
    avatar: Optional[str] = None
    timezone: str

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    """Profile update payload."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    timezone: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=10)
    theme: Optional[str] = Field(None, pattern="^(light|dark|system)$")
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")


class AdminUpdateUserRequest(BaseModel):
    """Admin-only user update."""

    status: Optional[str] = Field(None, pattern="^(active|inactive|suspended|admin)$")
    email_verified: Optional[bool] = None


class UserSearchResponse(BaseModel):
    """Compact user info for search results."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    avatar: Optional[str] = None

    model_config = {"from_attributes": True}
