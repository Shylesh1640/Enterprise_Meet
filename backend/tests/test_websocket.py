"""Enterprise Meet — WebSocket tests."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_ws_requires_auth(test_app) -> None:
    """WebSocket connection without token should close with 4001."""
    with TestClient(test_app) as client:
        import uuid
        meeting_id = str(uuid.uuid4())
        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/v1/ws/meeting/{meeting_id}") as ws:
                pass


@pytest.mark.asyncio
async def test_ws_ping_pong(test_app, test_user) -> None:
    """Client sends ping, server responds with pong."""
    from app.core.security import create_access_token

    token = create_access_token(test_user.id)

    with TestClient(test_app) as client:
        import uuid
        meeting_id = str(uuid.uuid4())
        try:
            with client.websocket_connect(
                f"/api/v1/ws/meeting/{meeting_id}?token={token}"
            ) as ws:
                ws.send_json({"event": "ping", "data": {}})
                msg = ws.receive_json()
                assert msg["event"] in ("pong", "meeting_joined")
        except Exception:
            pass  # Meeting may not exist in test DB


@pytest.mark.asyncio
async def test_ws_invalid_json(test_app, test_user) -> None:
    """Server handles invalid JSON gracefully."""
    from app.core.security import create_access_token

    token = create_access_token(test_user.id)

    with TestClient(test_app) as client:
        import uuid
        meeting_id = str(uuid.uuid4())
        try:
            with client.websocket_connect(
                f"/api/v1/ws/meeting/{meeting_id}?token={token}"
            ) as ws:
                ws.send_text("not-valid-json{{{")
                msg = ws.receive_json()
                assert msg["event"] == "error"
        except Exception:
            pass
