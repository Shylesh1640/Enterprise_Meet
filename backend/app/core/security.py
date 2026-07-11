"""Enterprise Meet — Security utilities: JWT, password hashing, OTP."""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password Hashing ──────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def generate_random_password(length: int = 20) -> str:
    """Generate a cryptographically secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ── JWT Tokens ────────────────────────────────────────────────────────────────

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
TOKEN_TYPE_EMAIL_VERIFY = "email_verify"
TOKEN_TYPE_PASSWORD_RESET = "password_reset"


def create_access_token(
    subject: str | UUID,
    *,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Create a short-lived access JWT."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": TOKEN_TYPE_ACCESS,
        "jti": secrets.token_urlsafe(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | UUID) -> str:
    """Create a long-lived refresh JWT."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": TOKEN_TYPE_REFRESH,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)


def create_email_verify_token(subject: str | UUID) -> str:
    """Create a one-time email verification token (expires in 24h)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=24)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": TOKEN_TYPE_EMAIL_VERIFY,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_password_reset_token(subject: str | UUID) -> str:
    """Create a password reset token (expires in 1h)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=1)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": TOKEN_TYPE_PASSWORD_RESET,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access JWT. Raises JWTError on failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != TOKEN_TYPE_ACCESS:
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate a refresh JWT."""
    try:
        payload = jwt.decode(token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != TOKEN_TYPE_REFRESH:
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise


def decode_email_verify_token(token: str) -> dict[str, Any]:
    """Decode and validate an email verification token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != TOKEN_TYPE_EMAIL_VERIFY:
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise


def decode_password_reset_token(token: str) -> dict[str, Any]:
    """Decode and validate a password reset token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != TOKEN_TYPE_PASSWORD_RESET:
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise


def get_token_jti(token: str) -> str | None:
    """Extract JWT ID (jti) from token without full validation."""
    try:
        unverified = jwt.get_unverified_claims(token)
        return unverified.get("jti")
    except Exception:
        return None


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Generate a cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


def generate_secure_token(length: int = 32) -> str:
    """Generate a URL-safe secure token (for invites, etc.)."""
    return secrets.token_urlsafe(length)


# ── Meeting Code ──────────────────────────────────────────────────────────────

def generate_meeting_code() -> str:
    """Generate a unique meeting code in format: xxx-xxxx-xxx."""
    chars = string.ascii_lowercase + string.digits
    part1 = "".join(secrets.choice(chars) for _ in range(3))
    part2 = "".join(secrets.choice(chars) for _ in range(4))
    part3 = "".join(secrets.choice(chars) for _ in range(3))
    return f"{part1}-{part2}-{part3}"
