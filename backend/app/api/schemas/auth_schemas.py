"""
Pydantic v2 request/response schemas for auth endpoints.

Separate from DTOs:
  - Schemas = HTTP contract (validation + OpenAPI docs)
  - DTOs    = internal service contract (no HTTP coupling)
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Requests ───────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email:             EmailStr      = Field(..., description="User email address")
    password:          str           = Field(..., min_length=8, max_length=128)
    full_name:         str           = Field(..., min_length=1, max_length=255)
    organization_name: str           = Field(..., min_length=1, max_length=255, alias="organization_name")
    organization_slug: str           = Field(
        ...,
        min_length=4,
        max_length=63,
        pattern=r"^[a-z0-9][a-z0-9\-]{2,61}[a-z0-9]$",
        description="URL-safe org identifier. Lowercase, alphanumeric and hyphens.",
    )

    model_config = {"populate_by_name": True}

    @field_validator("full_name", "organization_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    email:    EmailStr = Field(...)
    password: str      = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password:     str = Field(..., min_length=8, max_length=128)


# ── Responses ──────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token:  str = Field(..., description="JWT access token (15-minute lifetime)")
    refresh_token: str = Field(..., description="Opaque refresh token (7-day lifetime)")
    token_type:    str = Field(default="bearer")
    expires_in:    int = Field(default=900, description="Access token lifetime in seconds")


class UserResponse(BaseModel):
    id:             str
    email:          str
    full_name:      str
    role:           str
    mfa_enabled:    bool
    email_verified: bool
    created_at:     datetime
    last_login_at:  datetime | None = None

    model_config = {"from_attributes": True}


class OrganizationResponse(BaseModel):
    id:                   str
    name:                 str
    slug:                 str
    plan_tier:            str
    max_assets:           int
    max_users:            int
    max_concurrent_scans: int
    created_at:           datetime

    model_config = {"from_attributes": True}


class RegisterResponse(BaseModel):
    user:         UserResponse
    organization: OrganizationResponse
    tokens:       TokenResponse


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error:   str
    detail:  str | None = None
    code:    str | None = None
