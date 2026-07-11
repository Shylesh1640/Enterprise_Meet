"""Enterprise Meet — Users API router."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.dependencies import AdminUser, CurrentUser, DBSession, Pagination
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.user import AdminUpdateUserRequest, UpdateProfileRequest, UserPublicResponse, UserResponse, UserSearchResponse
from app.services.services import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=APIResponse[PaginatedResponse[UserResponse]],
    summary="List all users (admin only)",
)
async def list_users(
    admin: AdminUser,
    db: DBSession,
    pagination: Pagination,
) -> APIResponse:
    svc = UserService(db)
    users, total = await svc.list_users(page=pagination.page, page_size=pagination.page_size)
    meta = PaginationMeta.from_total(total, pagination.page, pagination.page_size)
    return APIResponse.ok(
        data=PaginatedResponse(
            items=[UserResponse.from_orm(u) for u in users],
            pagination=meta,
        )
    )


@router.get(
    "/search",
    response_model=APIResponse[PaginatedResponse[UserSearchResponse]],
    summary="Search users by name or email",
)
async def search_users(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
    q: str = Query(min_length=2, description="Search query"),
) -> APIResponse:
    svc = UserService(db)
    users, total = await svc.search_users(q, page=pagination.page, page_size=pagination.page_size)
    meta = PaginationMeta.from_total(total, pagination.page, pagination.page_size)
    return APIResponse.ok(
        data=PaginatedResponse(
            items=[UserSearchResponse.model_validate(u.__dict__) for u in users],
            pagination=meta,
        )
    )


@router.get(
    "/{user_id}",
    response_model=APIResponse[UserPublicResponse],
    summary="Get user by ID",
)
async def get_user(
    user_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = UserService(db)
    user = await svc.get_user(user_id)
    return APIResponse.ok(data=UserPublicResponse.model_validate(user.__dict__))


@router.put(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="Update user profile (own or admin)",
)
async def update_user(
    user_id: UUID,
    payload: UpdateProfileRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    if current_user.id != user_id and current_user.status != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden")
    svc = UserService(db)
    user = await svc.get_user(user_id)
    updated = await svc.update_profile(user, payload)
    return APIResponse.ok(data=UserResponse.from_orm(updated))


@router.delete(
    "/{user_id}",
    response_model=APIResponse[None],
    summary="Delete a user account (admin only)",
)
async def delete_user(
    user_id: UUID,
    admin: AdminUser,
    db: DBSession,
) -> APIResponse:
    svc = UserService(db)
    user = await svc.get_user(user_id)
    await svc.delete_account(user)
    return APIResponse.ok(message="User deleted")
