"""Enterprise Meet — Main API v1 router, aggregating all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.users.router import router as users_router
from app.api.v1.meetings.router import router as meetings_router
from app.api.v1.admin.router import router as admin_router
from app.api.v1.other_routers import (
    chat_router,
    files_router,
    notifications_router,
    recordings_router,
)
from app.api.v1.ws import router as ws_router

api_router = APIRouter(prefix="/api/v1")

# Register all sub-routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(meetings_router)
api_router.include_router(chat_router)
api_router.include_router(recordings_router)
api_router.include_router(notifications_router)
api_router.include_router(files_router)
api_router.include_router(admin_router)
api_router.include_router(ws_router)
