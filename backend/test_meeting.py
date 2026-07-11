"""Test meeting creation end-to-end."""
import asyncio
import httpx
from app.core.database import engine
from sqlalchemy import text


async def test():
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET email_verified=true WHERE email='testuser@test.com'")
        )
    print("Email verified updated")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"email": "testuser@test.com", "password": "TestPass123!"},
            timeout=10,
        )
        print("Login status:", resp.status_code)
        data = resp.json()
        token = data.get("data", {}).get("access_token")
        print("Got token:", bool(token))

        resp2 = await client.post(
            "http://localhost:8000/api/v1/meetings",
            json={"title": "Test Meeting", "meeting_type": "instant"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        print("Create meeting status:", resp2.status_code)
        print("Create meeting response:", resp2.text[:2000])


asyncio.run(test())
