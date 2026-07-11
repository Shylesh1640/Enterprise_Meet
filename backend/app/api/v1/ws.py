"""Enterprise Meet — WebSocket endpoint for meeting rooms."""

from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_ws_user_id
from app.core.logging import get_logger
from app.repositories.user_repository import UserRepository
from app.repositories.participant_repository import ParticipantRepository
from app.services.meeting_service import MeetingService
from app.schemas.meeting import JoinMeetingRequest
from app.websocket.handlers import EventHandler
from app.websocket.manager import manager

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


def _ice_url(protocol: str, address: str) -> str:
    """Return an ICE URL without duplicating an already supplied protocol."""
    return address if address.startswith((f"{protocol}:", f"{protocol}s:")) else f"{protocol}:{address}"


@router.websocket("/ws/meeting/{meeting_id}")
async def meeting_websocket(
    websocket: WebSocket,
    meeting_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_ws_user_id),
) -> None:
    """
    WebSocket endpoint for real-time meeting communication.

    Authentication: pass ?token=<access_token> as query parameter.

    Protocol:
    - All messages are JSON: { "event": "...", "data": {...}, "ack_id": "..." }
    - Server broadcasts use same format.
    - Heartbeat: server sends "pong" every 30 seconds.
    """
    # Verify user exists
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        await websocket.close(code=4001, reason="User not found")
        return

    # Auto-join the meeting
    meeting_svc = MeetingService(db)
    try:
        await meeting_svc.join_meeting(
            meeting_id, user_id, JoinMeetingRequest()
        )
        await db.commit()
    except Exception as e:
        logger.warning("ws_join_meeting_failed", meeting_id=str(meeting_id), error=str(e))
        # Don't reject connection — they may still be a participant from REST join

    # Accept and register WebSocket
    conn = await manager.connect(websocket, user_id, meeting_id)
    handler = EventHandler(manager, db)

    # Notify room: participant joined
    await manager.broadcast_to_room(
        meeting_id,
        "participant_joined",
        {
            "user_id": str(user_id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar": user.avatar,
        },
        exclude_user=user_id,
    )

    # Send current meeting state to joining user
    participant_repo = ParticipantRepository(db)
    participants = await participant_repo.get_active_participants(meeting_id)
    await conn.send_json({
        "event": "meeting_joined",
        "data": {
            "meeting_id": str(meeting_id),
            "user_id": str(user_id),
            "participants": [
                {
                    "user_id": str(p.user_id),
                    "role": p.role.value,
                    "mic_enabled": p.mic_enabled,
                    "camera_enabled": p.camera_enabled,
                    "screen_sharing": p.screen_sharing,
                    "hand_raised": p.hand_raised,
                }
                for p in participants
            ],
            "turn_servers": [
                {
                    "urls": [
                        _ice_url("turn", __import__('app.core.config', fromlist=['settings']).settings.TURN_SERVER_URL),
                        _ice_url("stun", __import__('app.core.config', fromlist=['settings']).settings.STUN_SERVER_URL),
                    ],
                    "username": __import__('app.core.config', fromlist=['settings']).settings.TURN_SERVER_USERNAME,
                    "credential": __import__('app.core.config', fromlist=['settings']).settings.TURN_SERVER_CREDENTIAL,
                }
            ],
        },
    })

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(manager.heartbeat_loop(conn))

    try:
        while True:
            raw = await websocket.receive_text()
            await handler.handle(conn, raw)
    except WebSocketDisconnect:
        logger.info("ws_disconnected", user_id=str(user_id), meeting_id=str(meeting_id))
    except Exception as e:
        logger.error("ws_error", user_id=str(user_id), error=str(e))
    finally:
        heartbeat_task.cancel()
        await manager.disconnect(conn)

        # Notify room: participant left
        await manager.broadcast_to_room(
            meeting_id,
            "participant_left",
            {"user_id": str(user_id)},
        )

        # Update DB: mark left
        try:
            await meeting_svc.leave_meeting(meeting_id, user_id)
            await db.commit()
        except Exception as e:
            logger.error("ws_leave_meeting_failed", error=str(e))
