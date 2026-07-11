"""Enterprise Meet — WebSocket Connection Manager with Redis pub/sub for horizontal scaling."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set
from uuid import UUID

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.logging import get_logger
from app.core.redis import RedisKeys, get_redis_client

logger = get_logger(__name__)

HEARTBEAT_INTERVAL = 30  # seconds
CHANNEL_PREFIX = "meeting:"


class WebSocketConnection:
    """Represents a single WebSocket connection within a meeting room."""

    def __init__(self, websocket: WebSocket, user_id: UUID, meeting_id: UUID) -> None:
        self.ws = websocket
        self.user_id = user_id
        self.meeting_id = meeting_id
        self.connected_at = datetime.now(timezone.utc)
        self.last_heartbeat = datetime.now(timezone.utc)

    @property
    def is_open(self) -> bool:
        return self.ws.client_state == WebSocketState.CONNECTED

    async def send_json(self, data: dict[str, Any]) -> None:
        """Send JSON message, handle closed connection gracefully."""
        try:
            if self.is_open:
                await self.ws.send_json(data)
        except Exception as e:
            logger.warning("ws_send_failed", user_id=str(self.user_id), error=str(e))


class ConnectionManager:
    """
    Room-based WebSocket connection manager with Redis pub/sub for multi-instance broadcasting.
    - Each meeting is a "room" identified by meeting_id.
    - Local connections stored in memory; cross-instance broadcasts via Redis pub/sub.
    """

    def __init__(self) -> None:
        # meeting_id -> {user_id -> WebSocketConnection}
        self._rooms: Dict[str, Dict[str, WebSocketConnection]] = defaultdict(dict)
        self._pubsub_task: Optional[asyncio.Task] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the Redis pub/sub listener."""
        self._pubsub_task = asyncio.create_task(self._listen_redis())
        logger.info("ws_manager_started")

    async def stop(self) -> None:
        """Cancel the pub/sub listener."""
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
        logger.info("ws_manager_stopped")

    # ── Connect / Disconnect ──────────────────────────────────────────────────

    async def connect(
        self, websocket: WebSocket, user_id: UUID, meeting_id: UUID
    ) -> WebSocketConnection:
        """Accept a new WebSocket connection and add it to the room."""
        await websocket.accept()
        conn = WebSocketConnection(websocket, user_id, meeting_id)
        room_key = str(meeting_id)
        self._rooms[room_key][str(user_id)] = conn

        # Track in Redis
        r = get_redis_client()
        await r.sadd(RedisKeys.ws_connections(room_key), str(user_id))
        await r.expire(RedisKeys.ws_connections(room_key), 86400)

        logger.info(
            "ws_connected",
            user_id=str(user_id),
            meeting_id=room_key,
            room_size=len(self._rooms[room_key]),
        )
        return conn

    async def disconnect(self, conn: WebSocketConnection) -> None:
        """Remove a connection from the room."""
        room_key = str(conn.meeting_id)
        uid = str(conn.user_id)
        self._rooms[room_key].pop(uid, None)

        if not self._rooms[room_key]:
            del self._rooms[room_key]

        # Remove from Redis
        r = get_redis_client()
        await r.srem(RedisKeys.ws_connections(room_key), uid)

        logger.info("ws_disconnected", user_id=uid, meeting_id=room_key)

    # ── Broadcast ─────────────────────────────────────────────────────────────

    async def broadcast_to_room(
        self,
        meeting_id: str | UUID,
        event: str,
        data: dict[str, Any],
        *,
        exclude_user: Optional[UUID] = None,
    ) -> None:
        """Broadcast an event to all connections in a room (local + remote via Redis)."""
        room_key = str(meeting_id)
        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Local broadcast
        await self._local_broadcast(room_key, message, exclude_user=exclude_user)

        # Redis publish for other instances
        r = get_redis_client()
        payload = json.dumps({
            "room": room_key,
            "message": message,
            "exclude_user": str(exclude_user) if exclude_user else None,
        })
        await r.publish(f"{CHANNEL_PREFIX}{room_key}", payload)

    async def send_to_user(
        self,
        meeting_id: str | UUID,
        user_id: UUID,
        event: str,
        data: dict[str, Any],
    ) -> None:
        """Send an event to a specific user in a room."""
        room_key = str(meeting_id)
        conn = self._rooms.get(room_key, {}).get(str(user_id))
        if conn:
            await conn.send_json({"event": event, "data": data})

    async def _local_broadcast(
        self,
        room_key: str,
        message: dict[str, Any],
        *,
        exclude_user: Optional[UUID] = None,
    ) -> None:
        """Broadcast to all local connections in a room."""
        exclude_str = str(exclude_user) if exclude_user else None
        connections = list(self._rooms.get(room_key, {}).values())
        dead: list[WebSocketConnection] = []

        for conn in connections:
            if exclude_str and str(conn.user_id) == exclude_str:
                continue
            if conn.is_open:
                await conn.send_json(message)
            else:
                dead.append(conn)

        for dead_conn in dead:
            await self.disconnect(dead_conn)

    # ── Redis pub/sub listener ─────────────────────────────────────────────────

    async def _listen_redis(self) -> None:
        """Listen to Redis pub/sub for cross-instance broadcasts."""
        r = get_redis_client()
        pubsub = r.pubsub()
        await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
        logger.info("redis_pubsub_subscribed", pattern=f"{CHANNEL_PREFIX}*")

        try:
            async for raw_message in pubsub.listen():
                if raw_message["type"] != "pmessage":
                    continue
                try:
                    payload = json.loads(raw_message["data"])
                    room = payload.get("room", "")
                    message = payload.get("message", {})
                    exclude_user = payload.get("exclude_user")
                    exclude_id = UUID(exclude_user) if exclude_user else None
                    await self._local_broadcast(room, message, exclude_user=exclude_id)
                except Exception as e:
                    logger.error("redis_pubsub_message_error", error=str(e))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("redis_pubsub_listener_error", error=str(e))
        finally:
            await pubsub.aclose()

    # ── Heartbeat ─────────────────────────────────────────────────────────────

    async def heartbeat_loop(self, conn: WebSocketConnection) -> None:
        """Send periodic pings to detect stale connections."""
        while conn.is_open:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            if conn.is_open:
                await conn.send_json({"event": "pong", "data": {}})

    # ── Room Info ─────────────────────────────────────────────────────────────

    def get_room_user_ids(self, meeting_id: str | UUID) -> Set[str]:
        return set(self._rooms.get(str(meeting_id), {}).keys())

    def get_connection(self, meeting_id: str | UUID, user_id: UUID) -> Optional[WebSocketConnection]:
        return self._rooms.get(str(meeting_id), {}).get(str(user_id))

    @property
    def total_connections(self) -> int:
        return sum(len(room) for room in self._rooms.values())


# Singleton instance
manager = ConnectionManager()
