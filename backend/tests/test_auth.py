"""Enterprise Meet — Auth API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "NewUser@12345",
        "first_name": "New",
        "last_name": "User",
        "timezone": "UTC",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "user_id" in data["data"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user) -> None:
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "TestPassword@123",
        "first_name": "Test",
        "last_name": "User",
    })
    assert response.status_code == 409
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user) -> None:
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "TestPassword@123",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user) -> None:
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "WrongPassword@123",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_me_no_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/register", json={
        "email": "weak@example.com",
        "password": "weak",
        "first_name": "Weak",
        "last_name": "User",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user) -> None:
    login = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "TestPassword@123",
    })
    refresh_token = login.json()["data"]["refresh_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]
