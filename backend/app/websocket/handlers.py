"""Enterprise Meet — WebSocket event handlers (client -> server) and WebRTC signaling."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.websocket.manager import ConnectionManager, WebSocketConnection

logger = get_logger(__name__)


# ── Event Dispatcher ──────────────────────────────────────────────────────────

class EventHandler:
    """
    Handles all client→server WebSocket events and dispatches server→client events.
    All WebRTC signaling (offer, answer, ICE candidate) is forwarded peer-to-peer
    via the room broadcast.
    """

    def __init__(self, manager: ConnectionManager, db: AsyncSession) -> None:
        self._mgr = manager
        self._db = db

    async def handle(self, conn: WebSocketConnection, raw: str) -> None:
        """Parse incoming WebSocket message and route to the correct handler."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await conn.send_json({"event": "error", "data": {"message": "Invalid JSON"}})
            return

        event = msg.get("event", "")
        data = msg.get("data", {})
        ack_id = msg.get("ack_id")  # for message acknowledgements

        handler = getattr(self, f"_on_{event}", None)
        if handler:
            try:
                result = await handler(conn, data)
                if ack_id and result is not None:
                    await conn.send_json({"event": "ack", "ack_id": ack_id, "data": result})
            except Exception as e:
                logger.error("ws_event_handler_error", event=event, error=str(e))
                await conn.send_json({"event": "error", "data": {"message": str(e)}})
        else:
            logger.warning("unknown_ws_event", event=event, user_id=str(conn.user_id))

    # ── Chat Events ───────────────────────────────────────────────────────────

    async def _on_send_message(self, conn: WebSocketConnection, data: dict[str, Any]) -> dict:
        from app.services.services import ChatService
        from app.schemas.responses import SendMessageRequest

        svc = ChatService(self._db)
        payload = SendMessageRequest(
            meeting_id=conn.meeting_id,
            message=data.get("message", ""),
            reply_to=data.get("reply_to"),
        )
        msg = await svc.send_message(conn.user_id, payload)
        await self._db.commit()

        broadcast_data = {
            "id": str(msg.id),
            "meeting_id": str(msg.meeting_id),
            "sender_id": str(conn.user_id),
            "message": msg.message,
            "reply_to": str(msg.reply_to) if msg.reply_to else None,
            "created_at": msg.created_at.isoformat(),
        }
        await self._mgr.broadcast_to_room(conn.meeting_id, "message_received", broadcast_data)
        return {"message_id": str(msg.id)}

    async def _on_edit_message(self, conn: WebSocketConnection, data: dict[str, Any]) -> dict:
        from app.services.services import ChatService
        from app.schemas.responses import EditMessageRequest

        message_id = UUID(data["message_id"])
        svc = ChatService(self._db)
        msg = await svc.edit_message(message_id, conn.user_id, EditMessageRequest(message=data["message"]))
        await self._db.commit()

        await self._mgr.broadcast_to_room(conn.meeting_id, "message_edited", {
            "id": str(msg.id),
            "message": msg.message,
            "edited": True,
        })
        return {"ok": True}

    async def _on_delete_message(self, conn: WebSocketConnection, data: dict[str, Any]) -> dict:
        from app.services.services import ChatService

        message_id = UUID(data["message_id"])
        svc = ChatService(self._db)
        await svc.delete_message(message_id, conn.user_id)
        await self._db.commit()

        await self._mgr.broadcast_to_room(conn.meeting_id, "message_deleted", {
            "id": str(message_id),
        })
        return {"ok": True}

    # ── Typing ────────────────────────────────────────────────────────────────

    async def _on_typing_start(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        await self._mgr.broadcast_to_room(
            conn.meeting_id,
            "typing",
            {"user_id": str(conn.user_id), "is_typing": True},
            exclude_user=conn.user_id,
        )

    async def _on_typing_stop(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        await self._mgr.broadcast_to_room(
            conn.meeting_id,
            "typing",
            {"user_id": str(conn.user_id), "is_typing": False},
            exclude_user=conn.user_id,
        )

    # ── Hand Raise ────────────────────────────────────────────────────────────

    async def _on_raise_hand(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        await self._update_participant_state(conn, hand_raised=True)
        await self._mgr.broadcast_to_room(
            conn.meeting_id, "hand_raised", {"user_id": str(conn.user_id)}
        )

    async def _on_lower_hand(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        await self._update_participant_state(conn, hand_raised=False)
        await self._mgr.broadcast_to_room(
            conn.meeting_id, "hand_lowered", {"user_id": str(conn.user_id)}
        )

    # ── Media State ───────────────────────────────────────────────────────────

    async def _on_toggle_mic(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        enabled = bool(data.get("enabled", False))
        await self._update_participant_state(conn, mic_enabled=enabled)
        await self._mgr.broadcast_to_room(
            conn.meeting_id,
            "mic_updated",
            {"user_id": str(conn.user_id), "enabled": enabled},
        )

    async def _on_toggle_camera(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        enabled = bool(data.get("enabled", False))
        await self._update_participant_state(conn, camera_enabled=enabled)
        await self._mgr.broadcast_to_room(
            conn.meeting_id,
            "camera_updated",
            {"user_id": str(conn.user_id), "enabled": enabled},
        )

    async def _on_start_screen_share(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        await self._update_participant_state(conn, screen_sharing=True)
        await self._mgr.broadcast_to_room(
            conn.meeting_id,
            "screen_share_started",
            {"user_id": str(conn.user_id)},
        )

    async def _on_stop_screen_share(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        await self._update_participant_state(conn, screen_sharing=False)
        await self._mgr.broadcast_to_room(
            conn.meeting_id,
            "screen_share_stopped",
            {"user_id": str(conn.user_id)},
        )

    # ── Recording ─────────────────────────────────────────────────────────────

    async def _on_start_recording(self, conn: WebSocketConnection, data: dict[str, Any]) -> dict:
        from app.services.services import RecordingService

        svc = RecordingService(self._db)
        rec = await svc.start_recording(conn.meeting_id, conn.user_id)
        await self._db.commit()

        await self._mgr.broadcast_to_room(
            conn.meeting_id,
            "recording_started",
            {"recording_id": str(rec.id), "started_by": str(conn.user_id)},
        )
        return {"recording_id": str(rec.id)}

    async def _on_stop_recording(self, conn: WebSocketConnection, data: dict[str, Any]) -> dict:
        from app.services.services import RecordingService

        recording_id = UUID(data["recording_id"])
        svc = RecordingService(self._db)
        rec = await svc.stop_recording(conn.meeting_id, recording_id, conn.user_id)
        await self._db.commit()

        await self._mgr.broadcast_to_room(
            conn.meeting_id,
            "recording_stopped",
            {"recording_id": str(rec.id)},
        )
        return {"ok": True}

    # ── Emoji Reaction ────────────────────────────────────────────────────────

    async def _on_emoji_reaction(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        await self._mgr.broadcast_to_room(
            conn.meeting_id,
            "reaction_received",
            {
                "user_id": str(conn.user_id),
                "emoji": data.get("emoji", "👍"),
            },
        )

    # ── Heartbeat ─────────────────────────────────────────────────────────────

    async def _on_ping(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        conn.last_heartbeat = datetime.now(timezone.utc)
        await conn.send_json({"event": "pong", "data": {"timestamp": datetime.now(timezone.utc).isoformat()}})

    # ── WebRTC Signaling ──────────────────────────────────────────────────────

    async def _on_offer(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        """Forward SDP offer to target peer."""
        target_id = data.get("target_id")
        if target_id:
            await self._mgr.send_to_user(
                conn.meeting_id,
                UUID(target_id),
                "offer",
                {"from": str(conn.user_id), "sdp": data.get("sdp"), "type": "offer"},
            )

    async def _on_answer(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        """Forward SDP answer to target peer."""
        target_id = data.get("target_id")
        if target_id:
            await self._mgr.send_to_user(
                conn.meeting_id,
                UUID(target_id),
                "answer",
                {"from": str(conn.user_id), "sdp": data.get("sdp"), "type": "answer"},
            )

    async def _on_ice_candidate(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        """Forward ICE candidate to target peer."""
        target_id = data.get("target_id")
        if target_id:
            await self._mgr.send_to_user(
                conn.meeting_id,
                UUID(target_id),
                "ice_candidate",
                {
                    "from": str(conn.user_id),
                    "candidate": data.get("candidate"),
                    "sdpMid": data.get("sdpMid"),
                    "sdpMLineIndex": data.get("sdpMLineIndex"),
                },
            )

    async def _on_renegotiate(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        """Forward renegotiation request to target peer."""
        target_id = data.get("target_id")
        if target_id:
            await self._mgr.send_to_user(
                conn.meeting_id,
                UUID(target_id),
                "renegotiate",
                {"from": str(conn.user_id), "sdp": data.get("sdp")},
            )

    async def _on_reconnect(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        """Signal peer reconnect to the room."""
        await self._mgr.broadcast_to_room(
            conn.meeting_id,
            "participant_updated",
            {"user_id": str(conn.user_id), "connection_status": "reconnecting"},
            exclude_user=conn.user_id,
        )

    # ── Leave / Join ──────────────────────────────────────────────────────────

    async def _on_leave_meeting(self, conn: WebSocketConnection, data: dict[str, Any]) -> None:
        from app.services.meeting_service import MeetingService

        svc = MeetingService(self._db)
        await svc.leave_meeting(conn.meeting_id, conn.user_id)
        await self._db.commit()

        await self._mgr.broadcast_to_room(
            conn.meeting_id,
            "participant_left",
            {"user_id": str(conn.user_id)},
            exclude_user=conn.user_id,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _update_participant_state(self, conn: WebSocketConnection, **fields: Any) -> None:
        """Update participant media state in the database."""
        from app.repositories.participant_repository import ParticipantRepository
        repo = ParticipantRepository(self._db)
        p = await repo.get_by_meeting_and_user(conn.meeting_id, conn.user_id)
        if p:
            for k, v in fields.items():
                setattr(p, k, v)
            await self._db.flush()
