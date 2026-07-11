"""Enterprise Meet — FastAPI dependency injection: auth, DB, rate limiting, RBAC."""

from __future__ import annotations

import time
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger, set_user_id
from app.core.redis import RedisKeys, get_redis_client, is_token_blacklisted
from app.core.security import decode_access_token

logger = get_logger(__name__)

# ── HTTP Bearer extractor ─────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)

CredentialsDep = Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


# ── Auth Dependencies ─────────────────────────────────────────────────────────

async def get_current_user_id(
    credentials: CredentialsDep,
    request: Request,
) -> UUID:
    """
    Extract and validate the JWT from Authorization header.
    Returns the user UUID from the token payload.
    Raises 401 if token is missing, invalid, or blacklisted.
    """
    auth_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials or not credentials.credentials:
        raise auth_exc

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub", "")
        jti: str = payload.get("jti", "")

        if not user_id_str:
            raise auth_exc

        # Check JWT blacklist
        if jti and await is_token_blacklisted(jti):
            logger.warning("blacklisted_token_used", jti=jti)
            raise auth_exc

        user_id = UUID(user_id_str)
        set_user_id(str(user_id))
        return user_id

    except (JWTError, ValueError) as exc:
        logger.warning("jwt_decode_failed", error=str(exc))
        raise auth_exc


async def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: DBSession,
) -> "User":  # type: ignore[name-defined]
    """
    Load the full User ORM object from DB.
    Raises 401 if user not found, 403 if account is inactive.
    """
    from app.repositories.user_repository import UserRepository

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deleted",
        )

    return user


async def get_current_active_user(
    current_user: Annotated["User", Depends(get_current_user)],  # type: ignore[name-defined]
) -> "User":  # type: ignore[name-defined]
    """Require user to have a verified email."""
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email first.",
        )
    return current_user


# ── WebSocket Auth ────────────────────────────────────────────────────────────

async def get_ws_user_id(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
) -> UUID:
    """
    Authenticate a WebSocket connection via ?token= query parameter.
    Closes the WebSocket with code 4001 on failure.
    """
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    try:
        payload = decode_access_token(token)
        jti = payload.get("jti", "")
        user_id_str = payload.get("sub", "")

        if not user_id_str:
            await websocket.close(code=4001, reason="Invalid token")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        if jti and await is_token_blacklisted(jti):
            await websocket.close(code=4001, reason="Token revoked")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        return UUID(user_id_str)

    except (JWTError, ValueError):
        await websocket.close(code=4001, reason="Invalid token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


# ── RBAC ──────────────────────────────────────────────────────────────────────

def require_role(*roles: str):
    """
    Factory for role-based access control dependencies.
    Usage: current_user: User = Depends(require_role("admin", "moderator"))
    """
    async def _check_role(
        current_user: Annotated["User", Depends(get_current_active_user)],  # type: ignore[name-defined]
    ) -> "User":  # type: ignore[name-defined]
        if current_user.status not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {', '.join(roles)}",
            )
        return current_user

    return _check_role


async def require_admin(
    current_user: Annotated["User", Depends(get_current_active_user)],  # type: ignore[name-defined]
) -> "User":  # type: ignore[name-defined]
    """Require admin status."""
    if current_user.status != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ── Rate Limiting ─────────────────────────────────────────────────────────────

class RateLimiter:
    """Sliding window rate limiter backed by Redis."""

    def __init__(self, limit: int, window_seconds: int, key_prefix: str = "ratelimit") -> None:
        self.limit = limit
        self.window = window_seconds
        self.key_prefix = key_prefix

    async def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path.replace("/", "_").strip("_")
        key = f"{self.key_prefix}:{client_ip}:{endpoint}"

        r = get_redis_client()
        now = int(time.time())
        window_start = now - self.window

        pipe = r.pipeline(transaction=True)
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, self.window)
        results = await pipe.execute()
        count: int = results[2]

        if count > self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {self.limit} requests per {self.window}s.",
                headers={"Retry-After": str(self.window)},
            )


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginationParams:
    """Common pagination query parameters."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number"),
        page_size: int = Query(
            default=settings.DEFAULT_PAGE_SIZE,
            ge=1,
            le=settings.MAX_PAGE_SIZE,
            description="Items per page",
        ),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


Pagination = Annotated[PaginationParams, Depends(PaginationParams)]

# ── Pre-built rate limiter instances ─────────────────────────────────────────

def _parse_rate_limit(value: str) -> tuple[int, int]:
    parts = value.split("/")
    limit = int(parts[0])
    unit = parts[1] if len(parts) > 1 else "minute"
    window = 1 if unit == "second" else 60
    return limit, window

auth_rate_limiter = RateLimiter(
    *_parse_rate_limit(settings.RATE_LIMIT_AUTH), key_prefix="auth"
)
api_rate_limiter = RateLimiter(
    *_parse_rate_limit(settings.RATE_LIMIT_API), key_prefix="api"
)
ws_rate_limiter = RateLimiter(
    *_parse_rate_limit(settings.RATE_LIMIT_WS), key_prefix="ws"
)

# ── Type Aliases ──────────────────────────────────────────────────────────────

CurrentUser = Annotated["User", Depends(get_current_active_user)]  # type: ignore[name-defined]
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
AdminUser = Annotated["User", Depends(require_admin)]  # type: ignore[name-defined]
