"""Enterprise Meet — Chat, Recordings, Notifications, Files API routers."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile, status

from app.core.dependencies import CurrentUser, DBSession, Pagination
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.responses import (
    AuditLogResponse,
    DashboardStats,
    EditMessageRequest,
    FileResponse,
    MarkNotificationsReadRequest,
    MessageResponse,
    NotificationResponse,
    RecordingResponse,
    SendMessageRequest,
    StartRecordingRequest,
    StopRecordingRequest,
    SystemHealth,
)
from app.services.services import (
    ChatService,
    FileService,
    NotificationService,
    RecordingService,
)

# ── Chat ──────────────────────────────────────────────────────────────────────

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


@chat_router.get(
    "/meetings/{meeting_id}/messages",
    response_model=APIResponse[PaginatedResponse[MessageResponse]],
    summary="Get meeting chat messages",
)
async def get_messages(
    meeting_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
) -> APIResponse:
    svc = ChatService(db)
    msgs, total = await svc.get_messages(
        meeting_id, current_user.id, page=pagination.page, page_size=pagination.page_size
    )
    meta = PaginationMeta.from_total(total, pagination.page, pagination.page_size)
    return APIResponse.ok(
        data=PaginatedResponse(
            items=[MessageResponse.model_validate(m.__dict__) for m in msgs],
            pagination=meta,
        )
    )


@chat_router.post(
    "/messages",
    response_model=APIResponse[MessageResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Send a chat message",
)
async def send_message(
    payload: SendMessageRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = ChatService(db)
    msg = await svc.send_message(current_user.id, payload)
    return APIResponse.ok(
        data=MessageResponse.model_validate(msg.__dict__), message="Message sent"
    )


@chat_router.put(
    "/messages/{message_id}",
    response_model=APIResponse[MessageResponse],
    summary="Edit a chat message",
)
async def edit_message(
    message_id: UUID,
    payload: EditMessageRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = ChatService(db)
    msg = await svc.edit_message(message_id, current_user.id, payload)
    return APIResponse.ok(data=MessageResponse.model_validate(msg.__dict__))


@chat_router.delete(
    "/messages/{message_id}",
    response_model=APIResponse[None],
    summary="Delete a chat message",
)
async def delete_message(
    message_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = ChatService(db)
    await svc.delete_message(message_id, current_user.id)
    return APIResponse.ok(message="Message deleted")


# ── Recordings ────────────────────────────────────────────────────────────────

recordings_router = APIRouter(prefix="/recordings", tags=["Recordings"])


@recordings_router.post(
    "/start",
    response_model=APIResponse[RecordingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Start recording a meeting",
)
async def start_recording(
    payload: StartRecordingRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = RecordingService(db)
    rec = await svc.start_recording(payload.meeting_id, current_user.id)
    return APIResponse.ok(data=RecordingResponse.model_validate(rec.__dict__))


@recordings_router.post(
    "/stop",
    response_model=APIResponse[RecordingResponse],
    summary="Stop an active recording",
)
async def stop_recording(
    payload: StopRecordingRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = RecordingService(db)
    rec = await svc.stop_recording(payload.meeting_id, payload.recording_id, current_user.id)
    return APIResponse.ok(data=RecordingResponse.model_validate(rec.__dict__))


@recordings_router.get(
    "",
    response_model=APIResponse[PaginatedResponse[RecordingResponse]],
    summary="List recordings for a meeting",
)
async def list_recordings(
    meeting_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
) -> APIResponse:
    svc = RecordingService(db)
    recs, total = await svc.list_recordings(
        meeting_id, page=pagination.page, page_size=pagination.page_size
    )
    meta = PaginationMeta.from_total(total, pagination.page, pagination.page_size)
    return APIResponse.ok(
        data=PaginatedResponse(
            items=[RecordingResponse.model_validate(r.__dict__) for r in recs],
            pagination=meta,
        )
    )


@recordings_router.get(
    "/{recording_id}",
    response_model=APIResponse[RecordingResponse],
    summary="Get recording by ID",
)
async def get_recording(
    recording_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = RecordingService(db)
    rec = await svc.get_recording(recording_id, current_user.id)
    return APIResponse.ok(data=RecordingResponse.model_validate(rec.__dict__))


@recordings_router.delete(
    "/{recording_id}",
    response_model=APIResponse[None],
    summary="Delete a recording",
)
async def delete_recording(
    recording_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = RecordingService(db)
    await svc.delete_recording(recording_id, current_user.id)
    return APIResponse.ok(message="Recording deleted")


# ── Notifications ─────────────────────────────────────────────────────────────

notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@notifications_router.get(
    "",
    response_model=APIResponse[PaginatedResponse[NotificationResponse]],
    summary="Get user notifications",
)
async def list_notifications(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
    unread_only: bool = Query(False),
) -> APIResponse:
    svc = NotificationService(db)
    notifs, total = await svc.list_notifications(
        current_user.id,
        page=pagination.page,
        page_size=pagination.page_size,
        unread_only=unread_only,
    )
    meta = PaginationMeta.from_total(total, pagination.page, pagination.page_size)
    return APIResponse.ok(
        data=PaginatedResponse(
            items=[NotificationResponse.model_validate(n.__dict__) for n in notifs],
            pagination=meta,
        )
    )


@notifications_router.put(
    "/read",
    response_model=APIResponse[dict],
    summary="Mark notifications as read",
)
async def mark_read(
    payload: MarkNotificationsReadRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = NotificationService(db)
    count = await svc.mark_read(current_user.id, payload)
    return APIResponse.ok(data={"marked_read": count})


@notifications_router.delete(
    "",
    response_model=APIResponse[dict],
    summary="Delete all notifications",
)
async def delete_notifications(
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = NotificationService(db)
    count = await svc.delete_notifications(current_user.id)
    return APIResponse.ok(data={"deleted": count})


# ── Files ─────────────────────────────────────────────────────────────────────

files_router = APIRouter(prefix="/files", tags=["Files"])


@files_router.post(
    "/upload",
    response_model=APIResponse[FileResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to a meeting",
)
async def upload_file(
    meeting_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(...),
) -> APIResponse:
    svc = FileService(db)
    uploaded = await svc.upload_file(meeting_id, current_user.id, file)
    return APIResponse.ok(data=FileResponse.model_validate(uploaded.__dict__))


@files_router.get(
    "",
    response_model=APIResponse[PaginatedResponse[FileResponse]],
    summary="List files for a meeting",
)
async def list_files(
    meeting_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
) -> APIResponse:
    svc = FileService(db)
    files, total = await svc.list_files(
        meeting_id, page=pagination.page, page_size=pagination.page_size
    )
    meta = PaginationMeta.from_total(total, pagination.page, pagination.page_size)
    return APIResponse.ok(
        data=PaginatedResponse(
            items=[FileResponse.model_validate(f.__dict__) for f in files],
            pagination=meta,
        )
    )


@files_router.delete(
    "/{file_id}",
    response_model=APIResponse[None],
    summary="Delete a file",
)
async def delete_file(
    file_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = FileService(db)
    await svc.delete_file(file_id, current_user.id)
    return APIResponse.ok(message="File deleted")
