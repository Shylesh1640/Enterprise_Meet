"""Enterprise Meet — Meeting / Participant / Settings / Invitation Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Meeting Settings ──────────────────────────────────────────────────────────

class MeetingSettingsSchema(BaseModel):
    allow_chat: bool = True
    allow_screen_share: bool = True
    allow_recording: bool = True
    allow_unmute: bool = True
    allow_camera: bool = True
    waiting_room: bool = False
    allow_reactions: bool = True
    allow_polls: bool = True
    allow_hand_raise: bool = True
    mute_on_entry: bool = False
    video_off_on_entry: bool = False

    model_config = {"from_attributes": True}


# ── Meeting ───────────────────────────────────────────────────────────────────

class CreateMeetingRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    meeting_type: str = Field(default="instant", pattern="^(instant|scheduled|recurring|webinar)$")
    meeting_password: Optional[str] = Field(None, max_length=64)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    recording_enabled: bool = False
    waiting_room: bool = False
    settings: Optional[MeetingSettingsSchema] = None


class UpdateMeetingRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    recording_enabled: Optional[bool] = None
    waiting_room: Optional[bool] = None
    settings: Optional[MeetingSettingsSchema] = None


class MeetingResponse(BaseModel):
    id: UUID
    host_id: UUID
    title: str
    description: Optional[str] = None
    meeting_code: str
    meeting_type: str
    status: str
    recording_enabled: bool
    waiting_room: bool
    locked: bool
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    created_at: datetime
    settings: Optional[MeetingSettingsSchema] = None
    participant_count: int = 0

    model_config = {"from_attributes": True}


class JoinMeetingRequest(BaseModel):
    meeting_password: Optional[str] = None


class InviteUserRequest(BaseModel):
    user_ids: Optional[List[UUID]] = None
    emails: Optional[List[str]] = None

    model_config = {"from_attributes": True}


# ── Participant ───────────────────────────────────────────────────────────────

class ParticipantResponse(BaseModel):
    id: UUID
    meeting_id: UUID
    user_id: UUID
    role: str
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None
    mic_enabled: bool
    camera_enabled: bool
    screen_sharing: bool
    hand_raised: bool
    connection_status: str

    model_config = {"from_attributes": True}


# ── Invitation ────────────────────────────────────────────────────────────────

class InvitationResponse(BaseModel):
    id: UUID
    meeting_id: UUID
    user_id: UUID
    status: str
    invited_at: datetime
    accepted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
