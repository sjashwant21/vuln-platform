"""
Authentication router — /v1/auth/*

Routes are intentionally thin:
  - Parse + validate HTTP input (Pydantic handles this)
  - Extract HTTP context (IP, User-Agent) — only the HTTP layer knows these
  - Call the service
  - Return the response schema

All business logic, password policy, and token management live in AuthService.
"""
from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request, status

from app.api.schemas.auth_schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
    OrganizationResponse,
)
from app.application.dto.auth_dto import (
    ChangePasswordInput,
    LoginInput,
    RefreshInput,
    RegisterInput,
)
from app.dependencies import AuthSvc, CurrentUser

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_client_ip(request: Request) -> str | None:
    """Extract real IP, respecting X-Forwarded-For from trusted proxies."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


# ── POST /auth/register ────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organisation and owner account",
)
async def register(
    body:    RegisterRequest,
    service: AuthSvc,
    request: Request,
) -> RegisterResponse:
    user_dto, org_dto = await service.register(
        RegisterInput(
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            organization_name=body.organization_name,
            organization_slug=body.organization_slug,
        )
    )
    # Issue a token pair immediately so the client doesn't need to login again
    tokens = await service.login(
        LoginInput(
            email=body.email,
            password=body.password,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
    )
    return RegisterResponse(
        user=UserResponse(
            id=user_dto.id,
            email=user_dto.email,
            full_name=user_dto.full_name,
            role=user_dto.role,
            mfa_enabled=user_dto.mfa_enabled,
            email_verified=user_dto.email_verified,
            created_at=user_dto.created_at,
            last_login_at=user_dto.last_login_at,
        ),
        organization=OrganizationResponse(
            id=org_dto.id,
            name=org_dto.name,
            slug=org_dto.slug,
            plan_tier=org_dto.plan_tier,
            max_assets=org_dto.max_assets,
            max_users=org_dto.max_users,
            max_concurrent_scans=org_dto.max_concurrent_scans,
            created_at=org_dto.created_at,
        ),
        tokens=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
        ),
    )


# ── POST /auth/login ───────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a token pair",
)
async def login(
    body:    LoginRequest,
    service: AuthSvc,
    request: Request,
) -> TokenResponse:
    tokens = await service.login(
        LoginInput(
            email=body.email,
            password=body.password,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
    )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


# ── POST /auth/refresh ─────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and get a new access token",
)
async def refresh_token(
    body:    RefreshRequest,
    service: AuthSvc,
    request: Request,
) -> TokenResponse:
    tokens = await service.refresh(
        RefreshInput(
            refresh_token=body.refresh_token,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
    )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


# ── POST /auth/logout ──────────────────────────────────────────

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke the current refresh token",
)
async def logout(
    body:         LogoutRequest,
    service:      AuthSvc,
    current_user: CurrentUser,
) -> MessageResponse:
    await service.logout(
        refresh_token=body.refresh_token,
        current_user=current_user,
    )
    return MessageResponse(message="Logged out successfully")


# ── POST /auth/change-password ─────────────────────────────────

@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change the authenticated user's password",
)
async def change_password(
    body:         ChangePasswordRequest,
    service:      AuthSvc,
    current_user: CurrentUser,
) -> MessageResponse:
    await service.change_password(
        ChangePasswordInput(
            user_id=current_user.user_id,
            org_id=current_user.org_id,
            current_password=body.current_password,
            new_password=body.new_password,
        )
    )
    return MessageResponse(message="Password changed. All sessions have been revoked.")


# ── GET /auth/me ───────────────────────────────────────────────

@router.get(
    "/me",
    summary="Return the current user's identity from the JWT",
)
async def get_me(current_user: CurrentUser) -> dict:
    """Lightweight endpoint — decodes the token only, no DB hit."""
    return {
        "user_id": current_user.user_id,
        "org_id":  current_user.org_id,
        "role":    current_user.role,
        "email":   current_user.email,
    }
