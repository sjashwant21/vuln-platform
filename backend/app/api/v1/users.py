"""
User management router — /v1/users/*

All routes require authentication.
Role enforcement uses the require_role() dependency factory.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status, Response

from app.api.schemas.user_schemas import (
    ChangeRoleRequest,
    UpdateProfileRequest,
    UserListResponse,
    UserResponse,
)
from app.dependencies import CurrentUser, UserSvc, require_role
from app.domain.enums import UserRole

router = APIRouter(prefix="/users", tags=["Users"])


# ── GET /users/me ──────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_my_profile(
    current_user: CurrentUser,
    service:      UserSvc,
) -> UserResponse:
    dto = await service.get_user(current_user.user_id, current_user.org_id)
    return UserResponse(
        id=dto.id,
        org_id=dto.org_id,
        email=dto.email,
        full_name=dto.full_name,
        role=dto.role,
        mfa_enabled=dto.mfa_enabled,
        email_verified=dto.email_verified,
        is_active=dto.is_active,
        last_login_at=dto.last_login_at,
        created_at=dto.created_at,
    )


# ── PATCH /users/me ────────────────────────────────────────────

@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_my_profile(
    body:         UpdateProfileRequest,
    current_user: CurrentUser,
    service:      UserSvc,
) -> UserResponse:
    dto = await service.update_profile(
        user_id=current_user.user_id,
        org_id=current_user.org_id,
        full_name=body.full_name,
    )
    return UserResponse(
        id=dto.id,
        org_id=dto.org_id,
        email=dto.email,
        full_name=dto.full_name,
        role=dto.role,
        mfa_enabled=dto.mfa_enabled,
        email_verified=dto.email_verified,
        is_active=dto.is_active,
        last_login_at=dto.last_login_at,
        created_at=dto.created_at,
    )


# ── GET /users ─────────────────────────────────────────────────

@router.get(
    "",
    response_model=UserListResponse,
    summary="List all users in the organisation (admin+)",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.OWNER))],
)
async def list_users(
    current_user: CurrentUser,
    service:      UserSvc,
    limit:  int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0,  ge=0),
) -> UserListResponse:
    users, total = await service.list_users(
        org_id=current_user.org_id,
        limit=limit,
        offset=offset,
    )
    return UserListResponse(
        items=[
            UserResponse(
                id=u.id,
                org_id=u.org_id,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                mfa_enabled=u.mfa_enabled,
                email_verified=u.email_verified,
                is_active=u.is_active,
                last_login_at=u.last_login_at,
                created_at=u.created_at,
            )
            for u in users
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


# ── GET /users/{user_id} ───────────────────────────────────────

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a specific user (admin+)",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.OWNER))],
)
async def get_user(
    user_id:      str,
    current_user: CurrentUser,
    service:      UserSvc,
) -> UserResponse:
    dto = await service.get_user(user_id, current_user.org_id)
    return UserResponse(
        id=dto.id,
        org_id=dto.org_id,
        email=dto.email,
        full_name=dto.full_name,
        role=dto.role,
        mfa_enabled=dto.mfa_enabled,
        email_verified=dto.email_verified,
        is_active=dto.is_active,
        last_login_at=dto.last_login_at,
        created_at=dto.created_at,
    )


# ── PATCH /users/{user_id}/role ────────────────────────────────

@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Change a user's role (owner only)",
)
async def change_user_role(
    user_id:      str,
    body:         ChangeRoleRequest,
    current_user: CurrentUser,
    service:      UserSvc,
) -> UserResponse:
    try:
        new_role = UserRole(body.role)
    except ValueError:
        from app.domain.exceptions import ValidationError
        raise ValidationError("role", f"Invalid role '{body.role}'. Valid: analyst, admin")

    dto = await service.change_role(
        target_user_id=user_id,
        new_role=new_role,
        org_id=current_user.org_id,
        acting_user_id=current_user.user_id,
        acting_role=UserRole(current_user.role),
    )
    return UserResponse(
        id=dto.id,
        org_id=dto.org_id,
        email=dto.email,
        full_name=dto.full_name,
        role=dto.role,
        mfa_enabled=dto.mfa_enabled,
        email_verified=dto.email_verified,
        is_active=dto.is_active,
        last_login_at=dto.last_login_at,
        created_at=dto.created_at,
    )


# ── DELETE /users/{user_id} ────────────────────────────────────

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate a user (admin+)",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.OWNER))],
)
async def deactivate_user(
    user_id:      str,
    current_user: CurrentUser,
    service:      UserSvc,
) -> dict:
    await service.deactivate_user(
        target_user_id=user_id,
        org_id=current_user.org_id,
        acting_user_id=current_user.user_id,
        acting_role=UserRole(current_user.role),
    )
    return {"status": "User deactivated"}
