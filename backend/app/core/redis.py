"""Enterprise Meet — Async Redis client with helpers for JWT blacklist, sessions, presence."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Optional

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Connection Pool ───────────────────────────────────────────────────────────

_pool: Optional[ConnectionPool] = None
_client: Optional[aioredis.Redis] = None


def get_redis_client() -> aioredis.Redis:
    """Return the global async Redis client (lazy-initialized)."""
    global _pool, _client
    if _client is None:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            decode_responses=True,
        )
        _client = aioredis.Redis(connection_pool=_pool)
    return _client


async def close_redis() -> None:
    """Close the Redis connection pool gracefully."""
    global _client, _pool
    if _client:
        await _client.aclose()
        _client = None
    if _pool:
        await _pool.aclose()
        _pool = None


# ── Key Namespacing ───────────────────────────────────────────────────────────

class RedisKeys:
    """Centralized Redis key builder with consistent namespacing."""

    JWT_BLACKLIST = "jwt:blacklist:{jti}"
    SESSION = "session:{user_id}"
    OTP = "otp:{user_id}:{purpose}"
    MEETING_PRESENCE = "presence:meeting:{meeting_id}"
    USER_PRESENCE = "presence:user:{user_id}"
    RATE_LIMIT = "ratelimit:{identifier}:{endpoint}"
    WS_CONNECTIONS = "ws:connections:{meeting_id}"
    MEETING_STATE = "meeting:state:{meeting_id}"
    NOTIFICATION_QUEUE = "notif:queue:{user_id}"
    TYPING_INDICATOR = "typing:{meeting_id}:{user_id}"

    @classmethod
    def jwt_blacklist(cls, jti: str) -> str:
        return cls.JWT_BLACKLIST.format(jti=jti)

    @classmethod
    def session(cls, user_id: str) -> str:
        return cls.SESSION.format(user_id=user_id)

    @classmethod
    def otp(cls, user_id: str, purpose: str) -> str:
        return cls.OTP.format(user_id=user_id, purpose=purpose)

    @classmethod
    def meeting_presence(cls, meeting_id: str) -> str:
        return cls.MEETING_PRESENCE.format(meeting_id=meeting_id)

    @classmethod
    def user_presence(cls, user_id: str) -> str:
        return cls.USER_PRESENCE.format(user_id=user_id)

    @classmethod
    def rate_limit(cls, identifier: str, endpoint: str) -> str:
        return cls.RATE_LIMIT.format(identifier=identifier, endpoint=endpoint)

    @classmethod
    def ws_connections(cls, meeting_id: str) -> str:
        return cls.WS_CONNECTIONS.format(meeting_id=meeting_id)

    @classmethod
    def meeting_state(cls, meeting_id: str) -> str:
        return cls.MEETING_STATE.format(meeting_id=meeting_id)

    @classmethod
    def notification_queue(cls, user_id: str) -> str:
        return cls.NOTIFICATION_QUEUE.format(user_id=user_id)

    @classmethod
    def typing_indicator(cls, meeting_id: str, user_id: str) -> str:
        return cls.TYPING_INDICATOR.format(meeting_id=meeting_id, user_id=user_id)


# ── Generic Helpers ───────────────────────────────────────────────────────────

class RedisCache:
    """Wrapper with helper methods for common Redis operations."""

    def __init__(self, client: aioredis.Redis) -> None:
        self._r = client

    async def set(self, key: str, value: Any, *, ex: Optional[int] = None) -> None:
        """Set a string/JSON value with optional TTL in seconds."""
        if not isinstance(value, str):
            value = json.dumps(value)
        await self._r.set(key, value, ex=ex)

    async def get(self, key: str) -> Optional[str]:
        """Get a raw string value."""
        return await self._r.get(key)

    async def get_json(self, key: str) -> Optional[Any]:
        """Get and deserialize a JSON value."""
        raw = await self._r.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        if not keys:
            return 0
        return await self._r.delete(*keys)

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return bool(await self._r.exists(key))

    async def expire(self, key: str, seconds: int) -> bool:
        """Set TTL on an existing key."""
        return bool(await self._r.expire(key, seconds))

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key (-1 = no expiry, -2 = not found)."""
        return await self._r.ttl(key)

    async def incr(self, key: str) -> int:
        """Atomically increment a counter."""
        return await self._r.incr(key)

    async def sadd(self, key: str, *members: str) -> int:
        """Add members to a set."""
        return await self._r.sadd(key, *members)

    async def srem(self, key: str, *members: str) -> int:
        """Remove members from a set."""
        return await self._r.srem(key, *members)

    async def smembers(self, key: str) -> set[str]:
        """Get all members of a set."""
        return await self._r.smembers(key)

    async def scard(self, key: str) -> int:
        """Get the cardinality (count) of a set."""
        return await self._r.scard(key)

    async def hset(self, key: str, mapping: dict[str, Any]) -> int:
        """Set a hash."""
        str_mapping = {k: json.dumps(v) if not isinstance(v, str) else v for k, v in mapping.items()}
        return await self._r.hset(key, mapping=str_mapping)

    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get a hash field."""
        return await self._r.hget(key, field)

    async def hgetall(self, key: str) -> dict[str, str]:
        """Get all fields and values of a hash."""
        return await self._r.hgetall(key)

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete hash fields."""
        return await self._r.hdel(key, *fields)

    async def lpush(self, key: str, *values: str) -> int:
        """Push values to the left of a list."""
        return await self._r.lpush(key, *values)

    async def rpop(self, key: str) -> Optional[str]:
        """Pop from the right of a list."""
        return await self._r.rpop(key)

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        """Get a range from a list."""
        return await self._r.lrange(key, start, end)

    async def publish(self, channel: str, message: Any) -> int:
        """Publish a message to a Redis pub/sub channel."""
        if not isinstance(message, str):
            message = json.dumps(message)
        return await self._r.publish(channel, message)


# ── JWT Blacklist ─────────────────────────────────────────────────────────────

async def blacklist_token(jti: str, expires_in: int) -> None:
    """Add a JWT ID to the blacklist with TTL matching token expiry."""
    try:
        r = get_redis_client()
        await r.set(RedisKeys.jwt_blacklist(jti), "1", ex=expires_in)
    except Exception:
        logger.warning("redis_unavailable_blacklist_token", jti=jti)


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a JWT ID is in the blacklist."""
    try:
        r = get_redis_client()
        return bool(await r.exists(RedisKeys.jwt_blacklist(jti)))
    except Exception:
        logger.warning("redis_unavailable_check_blacklist", jti=jti)
        return False


# ── OTP Cache ─────────────────────────────────────────────────────────────────

async def store_otp(user_id: str, purpose: str, otp: str) -> None:
    """Store an OTP with expiry."""
    r = get_redis_client()
    ttl = settings.OTP_EXPIRE_MINUTES * 60
    await r.set(RedisKeys.otp(user_id, purpose), otp, ex=ttl)


async def verify_and_delete_otp(user_id: str, purpose: str, otp: str) -> bool:
    """Verify OTP and delete it atomically (one-time use)."""
    r = get_redis_client()
    key = RedisKeys.otp(user_id, purpose)
    stored = await r.get(key)
    if stored and stored == otp:
        await r.delete(key)
        return True
    return False


# ── Meeting Presence ──────────────────────────────────────────────────────────

async def add_to_meeting_presence(meeting_id: str, user_id: str) -> None:
    """Track a user joining a meeting room."""
    r = get_redis_client()
    key = RedisKeys.meeting_presence(meeting_id)
    await r.sadd(key, user_id)
    await r.expire(key, 86400)  # 24h cleanup


async def remove_from_meeting_presence(meeting_id: str, user_id: str) -> None:
    """Remove a user from meeting presence."""
    r = get_redis_client()
    await r.srem(RedisKeys.meeting_presence(meeting_id), user_id)


async def get_meeting_presence(meeting_id: str) -> set[str]:
    """Get all user IDs present in a meeting."""
    r = get_redis_client()
    return await r.smembers(RedisKeys.meeting_presence(meeting_id))


async def get_meeting_presence_count(meeting_id: str) -> int:
    """Get the count of participants in a meeting."""
    r = get_redis_client()
    return await r.scard(RedisKeys.meeting_presence(meeting_id))


# ── Health Check ──────────────────────────────────────────────────────────────

async def check_redis_connection() -> bool:
    """Health-check: verify Redis is reachable."""
    try:
        r = get_redis_client()
        await r.ping()
        return True
    except Exception:
        return False


# ── Module-level cache instance ───────────────────────────────────────────────

def get_cache() -> RedisCache:
    """Get a RedisCache helper instance."""
    return RedisCache(get_redis_client())
