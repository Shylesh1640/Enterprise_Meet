"""Enterprise Meet — Meeting API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_meeting(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.post("/api/v1/meetings", json={
        "title": "Test Meeting",
        "meeting_type": "instant",
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["title"] == "Test Meeting"
    assert "meeting_code" in data["data"]


@pytest.mark.asyncio
async def test_list_meetings(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.get("/api/v1/meetings", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data["data"]
    assert "pagination" in data["data"]


@pytest.mark.asyncio
async def test_get_meeting(client: AsyncClient, auth_headers: dict) -> None:
    # Create first
    create_resp = await client.post("/api/v1/meetings", json={
        "title": "My Meeting",
        "meeting_type": "instant",
    }, headers=auth_headers)
    meeting_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/meetings/{meeting_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["id"] == meeting_id


@pytest.mark.asyncio
async def test_create_meeting_no_auth(client: AsyncClient) -> None:
    response = await client.post("/api/v1/meetings", json={
        "title": "Unauthorized Meeting",
        "meeting_type": "instant",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_join_meeting(client: AsyncClient, auth_headers: dict) -> None:
    # Create
    create = await client.post("/api/v1/meetings", json={
        "title": "Join Test",
        "meeting_type": "instant",
    }, headers=auth_headers)
    meeting_id = create.json()["data"]["id"]

    response = await client.post(f"/api/v1/meetings/{meeting_id}/join", json={}, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_lock_unlock_meeting(client: AsyncClient, auth_headers: dict) -> None:
    create = await client.post("/api/v1/meetings", json={
        "title": "Lock Test",
        "meeting_type": "instant",
    }, headers=auth_headers)
    meeting_id = create.json()["data"]["id"]

    lock_resp = await client.post(f"/api/v1/meetings/{meeting_id}/lock", headers=auth_headers)
    assert lock_resp.status_code == 200
    assert lock_resp.json()["data"]["locked"] is True

    unlock_resp = await client.post(f"/api/v1/meetings/{meeting_id}/unlock", headers=auth_headers)
    assert unlock_resp.status_code == 200
    assert unlock_resp.json()["data"]["locked"] is False


@pytest.mark.asyncio
async def test_delete_meeting(client: AsyncClient, auth_headers: dict) -> None:
    create = await client.post("/api/v1/meetings", json={
        "title": "Delete Test",
        "meeting_type": "instant",
    }, headers=auth_headers)
    meeting_id = create.json()["data"]["id"]

    delete = await client.delete(f"/api/v1/meetings/{meeting_id}", headers=auth_headers)
    assert delete.status_code == 200

    get = await client.get(f"/api/v1/meetings/{meeting_id}", headers=auth_headers)
    assert get.status_code == 404
