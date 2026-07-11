"""Enterprise Meet — Auth API router."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.core.dependencies import (
    CurrentUser,
    DBSession,
    auth_rate_limiter,
    get_current_user,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.common import APIResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=APIResponse[dict],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limiter)],
    summary="Register a new user account",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: DBSession,
) -> APIResponse:
    svc = AuthService(db)
    result = await svc.register(payload, request)
    return APIResponse.ok(data=result, message="Registration successful")


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    dependencies=[Depends(auth_rate_limiter)],
    summary="Authenticate and receive JWT tokens",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: DBSession,
) -> APIResponse:
    svc = AuthService(db)
    tokens = await svc.login(payload, request)
    return APIResponse.ok(data=tokens, message="Login successful")


@router.post(
    "/logout",
    response_model=APIResponse[None],
    summary="Invalidate current tokens",
)
async def logout(
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
    authorization: Optional[str] = Header(default=None),
    x_refresh_token: Optional[str] = Header(default=None),
) -> APIResponse:
    svc = AuthService(db)
    access_token = ""
    if authorization and authorization.startswith("Bearer "):
        access_token = authorization[7:]
    await svc.logout(access_token, x_refresh_token, current_user.id)
    return APIResponse.ok(message="Logged out successfully")


@router.post(
    "/refresh",
    response_model=APIResponse[TokenResponse],
    dependencies=[Depends(auth_rate_limiter)],
    summary="Refresh access token using refresh token",
)
async def refresh(
    payload: RefreshTokenRequest,
    db: DBSession,
) -> APIResponse:
    svc = AuthService(db)
    tokens = await svc.refresh(payload)
    return APIResponse.ok(data=tokens, message="Token refreshed")


@router.post(
    "/verify-email",
    response_model=APIResponse[None],
    summary="Verify email address with token from email",
)
async def verify_email(
    payload: VerifyEmailRequest,
    db: DBSession,
) -> APIResponse:
    svc = AuthService(db)
    result = await svc.verify_email(payload)
    return APIResponse.ok(data=result, message=result.get("message", "Email verified"))


@router.post(
    "/forgot-password",
    response_model=APIResponse[None],
    dependencies=[Depends(auth_rate_limiter)],
    summary="Initiate password reset",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: DBSession,
) -> APIResponse:
    svc = AuthService(db)
    result = await svc.forgot_password(payload)
    return APIResponse.ok(data=result, message=result.get("message", ""))


@router.post(
    "/reset-password",
    response_model=APIResponse[None],
    summary="Complete password reset with token",
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: DBSession,
) -> APIResponse:
    svc = AuthService(db)
    result = await svc.reset_password(payload)
    return APIResponse.ok(data=result, message=result.get("message", "Password reset"))


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get current authenticated user",
)
async def me(current_user: CurrentUser) -> APIResponse:
    return APIResponse.ok(data=UserResponse.from_orm(current_user))


@router.put(
    "/profile",
    response_model=APIResponse[UserResponse],
    summary="Update current user profile",
)
async def update_profile(
    payload: "UpdateProfileRequest",  # noqa: F821
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    from app.services.services import UserService
    from app.schemas.user import UpdateProfileRequest as UPR

    svc = UserService(db)
    updated = await svc.update_profile(current_user, UPR(**payload.model_dump()))
    return APIResponse.ok(data=UserResponse.from_orm(updated))


@router.delete(
    "/account",
    response_model=APIResponse[None],
    summary="Soft-delete current user account",
)
async def delete_account(current_user: CurrentUser, db: DBSession) -> APIResponse:
    from app.services.services import UserService

    svc = UserService(db)
    await svc.delete_account(current_user)
    return APIResponse.ok(message="Account deleted")


@router.post(
    "/change-password",
    response_model=APIResponse[None],
    summary="Change password (requires current password)",
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> APIResponse:
    svc = AuthService(db)
    result = await svc.change_password(current_user, payload)
    return APIResponse.ok(data=result, message=result.get("message", ""))
