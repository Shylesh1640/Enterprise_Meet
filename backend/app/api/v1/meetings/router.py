"""Enterprise Meet — Meetings API router."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DBSession, Pagination
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.meeting import (
    CreateMeetingRequest,
    InviteUserRequest,
    JoinMeetingRequest,
    MeetingResponse,
    ParticipantResponse,
)
from app.services.meeting_service import MeetingService

router = APIRouter(prefix="/meetings", tags=["Meetings"])


def _meeting_response(m: object, participant_count: int = 0) -> MeetingResponse:
    from app.schemas.meeting import MeetingSettingsSchema, MeetingResponse as MR
    settings = None
    if hasattr(m, "settings") and m.settings:
        settings = MeetingSettingsSchema.model_validate(m.settings)
    return MR(
        id=m.id,
        host_id=m.host_id,
        title=m.title,
        description=m.description,
        meeting_code=m.meeting_code,
        meeting_type=m.meeting_type.value,
        status=m.status.value,
        recording_enabled=m.recording_enabled,
        waiting_room=m.waiting_room,
        locked=m.locked,
        scheduled_start=m.scheduled_start,
        scheduled_end=m.scheduled_end,
        actual_start=m.actual_start,
        actual_end=m.actual_end,
        created_at=m.created_at,
        settings=settings,
        participant_count=participant_count,
    )


@router.post(
    "",
    response_model=APIResponse[MeetingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new meeting",
)
async def create_meeting(
    payload: CreateMeetingRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = MeetingService(db)
    meeting = await svc.create_meeting(current_user.id, payload)
    return APIResponse.ok(data=_meeting_response(meeting), message="Meeting created")


@router.get(
    "",
    response_model=APIResponse[PaginatedResponse[MeetingResponse]],
    summary="List meetings for current user",
)
async def list_meetings(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
    meeting_status: Optional[str] = Query(None, alias="status"),
) -> APIResponse:
    svc = MeetingService(db)
    meetings, total = await svc.list_meetings(
        current_user.id,
        page=pagination.page,
        page_size=pagination.page_size,
        meeting_status=meeting_status,
    )
    meta = PaginationMeta.from_total(total, pagination.page, pagination.page_size)
    return APIResponse.ok(
        data=PaginatedResponse(
            items=[_meeting_response(m) for m in meetings],
            pagination=meta,
        )
    )


@router.get(
    "/history",
    response_model=APIResponse[PaginatedResponse[MeetingResponse]],
    summary="Get meeting participation history",
)
async def meeting_history(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
) -> APIResponse:
    svc = MeetingService(db)
    meetings, total = await svc.get_history(
        current_user.id, page=pagination.page, page_size=pagination.page_size
    )
    meta = PaginationMeta.from_total(total, pagination.page, pagination.page_size)
    return APIResponse.ok(
        data=PaginatedResponse(
            items=[_meeting_response(m) for m in meetings],
            pagination=meta,
        )
    )


@router.get(
    "/by-code/{meeting_code}",
    response_model=APIResponse[MeetingResponse],
    summary="Get meeting by code",
)
async def get_meeting_by_code(
    meeting_code: str,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = MeetingService(db)
    meeting = await svc.get_meeting_by_code(meeting_code)
    return APIResponse.ok(data=_meeting_response(meeting))

@router.get(
    "/{meeting_id}",
    response_model=APIResponse[MeetingResponse],
    summary="Get meeting by ID",
)
async def get_meeting(
    meeting_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = MeetingService(db)
    meeting = await svc.get_meeting(meeting_id, current_user.id)
    return APIResponse.ok(data=_meeting_response(meeting))


@router.put(
    "/{meeting_id}",
    response_model=APIResponse[MeetingResponse],
    summary="Update meeting (host only)",
)
async def update_meeting(
    meeting_id: UUID,
    payload: "UpdateMeetingRequest",  # noqa: F821
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    from app.schemas.meeting import UpdateMeetingRequest

    svc = MeetingService(db)
    meeting = await svc.update_meeting(meeting_id, current_user.id, UpdateMeetingRequest(**payload.model_dump()))
    return APIResponse.ok(data=_meeting_response(meeting))


@router.delete(
    "/{meeting_id}",
    response_model=APIResponse[None],
    summary="Delete meeting (host only)",
)
async def delete_meeting(
    meeting_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = MeetingService(db)
    await svc.delete_meeting(meeting_id, current_user.id)
    return APIResponse.ok(message="Meeting deleted")


@router.post(
    "/{meeting_id}/join",
    response_model=APIResponse[ParticipantResponse],
    summary="Join a meeting",
)
async def join_meeting(
    meeting_id: UUID,
    payload: JoinMeetingRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = MeetingService(db)
    participant = await svc.join_meeting(meeting_id, current_user.id, payload)
    return APIResponse.ok(
        data=ParticipantResponse(
            id=participant.id,
            meeting_id=participant.meeting_id,
            user_id=participant.user_id,
            role=participant.role.value,
            joined_at=participant.joined_at,
            left_at=participant.left_at,
            mic_enabled=participant.mic_enabled,
            camera_enabled=participant.camera_enabled,
            screen_sharing=participant.screen_sharing,
            hand_raised=participant.hand_raised,
            connection_status=participant.connection_status.value,
        ),
        message="Joined meeting",
    )


@router.post(
    "/{meeting_id}/leave",
    response_model=APIResponse[None],
    summary="Leave a meeting",
)
async def leave_meeting(
    meeting_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = MeetingService(db)
    await svc.leave_meeting(meeting_id, current_user.id)
    return APIResponse.ok(message="Left meeting")


@router.post(
    "/{meeting_id}/lock",
    response_model=APIResponse[MeetingResponse],
    summary="Lock meeting (host only)",
)
async def lock_meeting(
    meeting_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = MeetingService(db)
    meeting = await svc.lock_meeting(meeting_id, current_user.id)
    return APIResponse.ok(data=_meeting_response(meeting), message="Meeting locked")


@router.post(
    "/{meeting_id}/unlock",
    response_model=APIResponse[MeetingResponse],
    summary="Unlock meeting (host only)",
)
async def unlock_meeting(
    meeting_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = MeetingService(db)
    meeting = await svc.unlock_meeting(meeting_id, current_user.id)
    return APIResponse.ok(data=_meeting_response(meeting), message="Meeting unlocked")


@router.post(
    "/{meeting_id}/invite",
    response_model=APIResponse[dict],
    summary="Invite users to a meeting",
)
async def invite_users(
    meeting_id: UUID,
    payload: InviteUserRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = MeetingService(db)
    result = await svc.invite_users(meeting_id, current_user.id, payload)
    return APIResponse.ok(data=result, message=f"Invited {result['invited']} users")
