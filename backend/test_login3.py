import asyncio
import sys
sys.path.insert(0, '.')

async def test_login():
    from app.core.database import get_db, engine
    from app.services.auth_service import AuthService
    from app.schemas.auth import LoginRequest
    from fastapi import Request
    from unittest.mock import MagicMock
    
    # Create mock request
    mock_request = MagicMock()
    mock_request.client.host = '127.0.0.1'
    mock_request.headers.get = lambda x: 'test-agent'
    
    payload = LoginRequest(email='user@example.com', password='Admin@123')
    
    async for db in get_db():
        try:
            svc = AuthService(db)
            result = await svc.login(payload, mock_request)
            print('SUCCESS:', result)
        except Exception as e:
            import traceback
            print('ERROR TYPE:', type(e).__name__)
            print('ERROR:', str(e))
            traceback.print_exc()
        break

asyncio.run(test_login())
