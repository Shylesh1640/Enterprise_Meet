"""Enterprise Meet — Admin API router."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import AdminUser, DBSession, Pagination
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.responses import AuditLogResponse, DashboardStats, SystemHealth

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/dashboard",
    response_model=APIResponse[DashboardStats],
    summary="Get admin dashboard statistics",
)
async def dashboard(admin: AdminUser, db: DBSession) -> APIResponse:
    from app.repositories.user_repository import UserRepository
    from app.repositories.meeting_repository import MeetingRepository
    from app.repositories.misc_repositories import RecordingRepository, FileRepository

    user_repo = UserRepository(db)
    meeting_repo = MeetingRepository(db)
    rec_repo = RecordingRepository(db)
    file_repo = FileRepository(db)

    user_counts = await user_repo.count_by_status()
    meeting_counts = await meeting_repo.count_by_status()
    total_recordings = await rec_repo.count()
    total_files = await file_repo.count()
    rec_size = await rec_repo.get_total_size()
    file_size = await file_repo.get_total_size()

    stats = DashboardStats(
        total_users=sum(user_counts.values()),
        active_users=user_counts.get("active", 0),
        total_meetings=sum(meeting_counts.values()),
        active_meetings=meeting_counts.get("active", 0),
        total_recordings=total_recordings,
        total_files=total_files,
        storage_used_bytes=rec_size + file_size,
    )
    return APIResponse.ok(data=stats)


@router.get(
    "/system-health",
    response_model=APIResponse[SystemHealth],
    summary="Get system health status",
)
async def system_health(admin: AdminUser) -> APIResponse:
    import time
    from app.core.database import check_db_connection
    from app.core.redis import check_redis_connection
    from app.core.config import settings

    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()

    # Check MinIO
    storage_ok = "ok"
    try:
        from minio import Minio
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        client.list_buckets()
    except Exception:
        storage_ok = "degraded"

    health = SystemHealth(
        status="ok" if (db_ok and redis_ok) else "degraded",
        database="ok" if db_ok else "error",
        redis="ok" if redis_ok else "error",
        celery="ok",  # Would check via Celery inspect in production
        storage=storage_ok,
        version=settings.APP_VERSION,
        uptime_seconds=time.time(),
    )
    return APIResponse.ok(data=health)


@router.get(
    "/users",
    response_model=APIResponse[PaginatedResponse[dict]],
    summary="Admin: list all users with details",
)
async def admin_list_users(
    admin: AdminUser,
    db: DBSession,
    pagination: Pagination,
    status_filter: str = Query(None, alias="status"),
) -> APIResponse:
    from app.repositories.user_repository import UserRepository
    from app.schemas.user import UserResponse

    repo = UserRepository(db)
    users, total = await repo.paginate(
        page=pagination.page,
        page_size=pagination.page_size,
        filters={"status": status_filter} if status_filter else None,
    )
    meta = PaginationMeta.from_total(total, pagination.page, pagination.page_size)
    return APIResponse.ok(
        data=PaginatedResponse(
            items=[UserResponse.from_orm(u).model_dump() for u in users],
            pagination=meta,
        )
    )


@router.get(
    "/meetings",
    response_model=APIResponse[PaginatedResponse[dict]],
    summary="Admin: list all meetings",
)
async def admin_list_meetings(
    admin: AdminUser,
    db: DBSession,
    pagination: Pagination,
) -> APIResponse:
    from app.repositories.meeting_repository import MeetingRepository

    repo = MeetingRepository(db)
    meetings, total = await repo.paginate(page=pagination.page, page_size=pagination.page_size)
    meta = PaginationMeta.from_total(total, pagination.page, pagination.page_size)
    return APIResponse.ok(
        data=PaginatedResponse(
            items=[
                {
                    "id": str(m.id),
                    "title": m.title,
                    "meeting_code": m.meeting_code,
                    "host_id": str(m.host_id),
                    "status": m.status.value,
                    "created_at": m.created_at.isoformat(),
                }
                for m in meetings
            ],
            pagination=meta,
        )
    )


@router.get(
    "/audit-logs",
    response_model=APIResponse[PaginatedResponse[AuditLogResponse]],
    summary="Admin: get audit logs",
)
async def audit_logs(
    admin: AdminUser,
    db: DBSession,
    pagination: Pagination,
    action: str = Query(None),
    entity: str = Query(None),
) -> APIResponse:
    from app.repositories.misc_repositories import AuditLogRepository

    repo = AuditLogRepository(db)
    logs, total = await repo.get_paginated(
        page=pagination.page,
        page_size=pagination.page_size,
        action=action,
        entity=entity,
    )
    meta = PaginationMeta.from_total(total, pagination.page, pagination.page_size)
    return APIResponse.ok(
        data=PaginatedResponse(
            items=[AuditLogResponse.model_validate(log.__dict__) for log in logs],
            pagination=meta,
        )
    )
