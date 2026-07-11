"""Enterprise Meet — Auth Service: register, login, logout, refresh, email verify, password reset."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import (
    blacklist_token,
    get_redis_client,
    RedisKeys,
    store_otp,
    verify_and_delete_otp,
)
from app.core.security import (
    create_access_token,
    create_email_verify_token,
    create_password_reset_token,
    create_refresh_token,
    decode_email_verify_token,
    decode_password_reset_token,
    decode_refresh_token,
    generate_otp,
    get_password_hash,
    get_token_jti,
    verify_password,
)
from app.models.user import User, UserStatus
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.user import UserResponse

logger = get_logger(__name__)


class AuthService:
    """Handles all authentication business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._users = UserRepository(db)

    # ── Register ──────────────────────────────────────────────────────────────

    async def register(self, payload: RegisterRequest, request: Request) -> dict:
        """Create a new user account and send verification email."""
        # Check for duplicate email
        if await self._users.email_exists(payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        # Hash password + create verify token
        password_hash = get_password_hash(payload.password)
        verify_token = create_email_verify_token(payload.email)

        user = await self._users.create(
            email=payload.email.lower(),
            password_hash=password_hash,
            first_name=payload.first_name,
            last_name=payload.last_name,
            timezone=payload.timezone,
            email_verified=False,
            email_verify_token=verify_token,
            status=UserStatus.ACTIVE,
        )

        logger.info("user_registered", user_id=str(user.id), email=user.email)

        # Fire verification email via Celery
        try:
            from app.workers.email_tasks import send_verification_email
            send_verification_email.delay(
                str(user.id), user.email, user.first_name, verify_token
            )
        except Exception as e:
            logger.error("failed_to_queue_verification_email", error=str(e))

        # Log audit
        await self._audit(user.id, "register", "user", user.id, request)

        return {
            "user_id": str(user.id),
            "email": user.email,
            "message": "Registration successful. Please verify your email.",
        }

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, payload: LoginRequest, request: Request) -> TokenResponse:
        """Authenticate user, return token pair."""
        user = await self._users.get_by_email(payload.email)

        if not user or not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not verify_password(payload.password, user.password_hash):
            logger.warning("login_failed_bad_password", email=payload.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if user.is_deleted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deleted")

        if user.status == UserStatus.SUSPENDED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")

        # Create tokens
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        # Store refresh token in Redis
        r = get_redis_client()
        refresh_expires = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        refresh_jti = get_token_jti(refresh_token) or ""
        await r.set(
            RedisKeys.session(str(user.id)),
            json.dumps({"jti": refresh_jti, "token": refresh_token}),
            ex=refresh_expires,
        )

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await self._db.flush()

        logger.info("user_logged_in", user_id=str(user.id))
        await self._audit(user.id, "login", "user", user.id, request)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_expires_seconds,
        )

    # ── Logout ────────────────────────────────────────────────────────────────

    async def logout(self, access_token: str, refresh_token: Optional[str], user_id: UUID) -> None:
        """Blacklist current tokens and clear Redis session."""
        # Blacklist access token
        jti = get_token_jti(access_token)
        if jti:
            await blacklist_token(jti, settings.jwt_access_expires_seconds)

        # Blacklist refresh token
        if refresh_token:
            refresh_jti = get_token_jti(refresh_token)
            if refresh_jti:
                await blacklist_token(refresh_jti, settings.jwt_refresh_expires_seconds)

        # Remove session
        r = get_redis_client()
        await r.delete(RedisKeys.session(str(user_id)))

        logger.info("user_logged_out", user_id=str(user_id))

    # ── Refresh ───────────────────────────────────────────────────────────────

    async def refresh(self, payload: RefreshTokenRequest) -> TokenResponse:
        """Exchange a valid refresh token for a new token pair."""
        try:
            claims = decode_refresh_token(payload.refresh_token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user_id_str = claims.get("sub", "")
        jti = claims.get("jti", "")

        # Check blacklist
        from app.core.redis import is_token_blacklisted
        if jti and await is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        user = await self._users.get_by_id(UUID(user_id_str))
        if not user or user.is_deleted:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        # Rotate: blacklist old refresh token, issue new pair
        if jti:
            await blacklist_token(jti, settings.jwt_refresh_expires_seconds)

        new_access = create_access_token(user.id)
        new_refresh = create_refresh_token(user.id)

        # Update session
        r = get_redis_client()
        new_jti = get_token_jti(new_refresh) or ""
        await r.set(
            RedisKeys.session(str(user.id)),
            json.dumps({"jti": new_jti, "token": new_refresh}),
            ex=settings.jwt_refresh_expires_seconds,
        )

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=settings.jwt_access_expires_seconds,
        )

    # ── Verify Email ──────────────────────────────────────────────────────────

    async def verify_email(self, payload: VerifyEmailRequest) -> dict:
        """Verify a user's email address using the token from the verification email."""
        try:
            claims = decode_email_verify_token(payload.token)
            user_email = claims.get("sub", "")
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        user = await self._users.get_by_email(user_email)
        if not user:
            # Also check by token stored in DB
            user = await self._users.get_by_verify_token(payload.token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token",
            )

        if user.email_verified:
            return {"message": "Email already verified"}

        user.email_verified = True
        user.email_verify_token = None
        await self._db.flush()

        logger.info("email_verified", user_id=str(user.id))
        return {"message": "Email verified successfully"}

    # ── Forgot Password ───────────────────────────────────────────────────────

    async def forgot_password(self, payload: ForgotPasswordRequest) -> dict:
        """Initiate password reset for an existing email."""
        user = await self._users.get_by_email(payload.email)
        # Always return same message to prevent email enumeration
        if not user:
            return {"message": "If that email exists, a reset link has been sent"}

        reset_token = create_password_reset_token(user.id)
        user.password_reset_token = reset_token
        await self._db.flush()

        try:
            from app.workers.email_tasks import send_password_reset_email
            send_password_reset_email.delay(user.email, user.first_name, reset_token)
        except Exception as e:
            logger.error("failed_to_queue_reset_email", error=str(e))

        return {"message": "If that email exists, a reset link has been sent"}

    # ── Reset Password ────────────────────────────────────────────────────────

    async def reset_password(self, payload: ResetPasswordRequest) -> dict:
        """Complete password reset using token from email."""
        try:
            claims = decode_password_reset_token(payload.token)
            user_id_str = claims.get("sub", "")
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        user = await self._users.get_by_id(UUID(user_id_str))
        if not user or user.password_reset_token != payload.token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token",
            )

        user.password_hash = get_password_hash(payload.password)
        user.password_reset_token = None
        await self._db.flush()

        # Invalidate all sessions
        r = get_redis_client()
        await r.delete(RedisKeys.session(str(user.id)))

        logger.info("password_reset", user_id=str(user.id))
        return {"message": "Password reset successfully"}

    # ── Change Password ───────────────────────────────────────────────────────

    async def change_password(
        self, user: User, payload: ChangePasswordRequest
    ) -> dict:
        """Change password for an authenticated user."""
        if not user.password_hash or not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        user.password_hash = get_password_hash(payload.new_password)
        await self._db.flush()

        logger.info("password_changed", user_id=str(user.id))
        return {"message": "Password changed successfully"}

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _audit(
        self,
        user_id: UUID,
        action: str,
        entity: str,
        entity_id: UUID,
        request: Request,
    ) -> None:
        """Write an audit log entry."""
        try:
            from app.repositories.misc_repositories import AuditLogRepository
            repo = AuditLogRepository(self._db)
            ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent")
            await repo.log(
                user_id=user_id,
                action=action,
                entity=entity,
                entity_id=entity_id,
                ip=ip,
                user_agent=ua,
            )
        except Exception as e:
            logger.error("audit_log_failed", error=str(e))
