"""Enterprise Meet — Message, Recording, Notification, File, Admin Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Messages ──────────────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    meeting_id: UUID
    message: str = Field(min_length=1, max_length=4000)
    reply_to: Optional[UUID] = None


class EditMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    id: UUID
    meeting_id: UUID
    sender_id: Optional[UUID] = None
    message: str
    edited: bool
    deleted: bool
    reply_to: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Recordings ────────────────────────────────────────────────────────────────

class StartRecordingRequest(BaseModel):
    meeting_id: UUID


class StopRecordingRequest(BaseModel):
    meeting_id: UUID
    recording_id: UUID


class RecordingResponse(BaseModel):
    id: UUID
    meeting_id: UUID
    file_url: Optional[str] = None
    duration: Optional[int] = None
    size: Optional[int] = None
    status: str
    thumbnail_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Notifications ─────────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: UUID
    title: str
    body: str
    type: str
    read: bool
    action_url: Optional[str] = None
    entity_id: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MarkNotificationsReadRequest(BaseModel):
    notification_ids: Optional[List[UUID]] = None  # None = mark all


# ── Files ─────────────────────────────────────────────────────────────────────

class FileResponse(BaseModel):
    id: UUID
    meeting_id: UUID
    uploaded_by: Optional[UUID] = None
    filename: str
    original_filename: str
    file_url: str
    mime_type: str
    size: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Admin ─────────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_meetings: int
    active_meetings: int
    total_recordings: int
    total_files: int
    storage_used_bytes: int


class SystemHealth(BaseModel):
    status: str
    database: str
    redis: str
    celery: str
    storage: str
    version: str
    uptime_seconds: float


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    action: str
    entity: str
    entity_id: Optional[UUID] = None
    ip: Optional[str] = None
    device: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
