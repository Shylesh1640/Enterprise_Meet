import asyncio
import aiohttp

async def test():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            'http://localhost:8000/api/v1/auth/login',
            json={'email': 'user@example.com', 'password': 'Admin@123'},
            headers={'Origin': 'http://localhost:5174'}
        ) as resp:
            print('Status:', resp.status)
            text = await resp.text()
            print('Body:', text[:2000])

asyncio.run(test())
