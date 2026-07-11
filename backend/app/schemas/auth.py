"""Enterprise Meet — Auth Pydantic schemas."""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ── Validators ────────────────────────────────────────────────────────────────

_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,64}$"
)


def validate_password_strength(password: str) -> str:
    if not _PASSWORD_PATTERN.match(password):
        raise ValueError(
            "Password must be 8-64 chars and contain uppercase, lowercase, digit, and special char"
        )
    return password


# ── Request Schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Registration payload."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    timezone: str = Field(default="UTC", max_length=100)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    """Login payload — accepts email or username."""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=64)
    remember_me: bool = False

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=64)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return validate_password_strength(v)


# ── Response Schemas ──────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """JWT token pair returned on login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserMeResponse(BaseModel):
    """Minimal user info returned by /auth/me."""

    id: str
    email: str
    first_name: str
    last_name: str
    avatar: Optional[str] = None
    email_verified: bool
    status: str

    model_config = {"from_attributes": True}
