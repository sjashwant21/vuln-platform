"""Pydantic v2 schemas for user and organisation endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ── Requests ───────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)


class ChangeRoleRequest(BaseModel):
    role: str = Field(..., description="New role: analyst | admin (owner via billing portal only)")


class UpdateOrgRequest(BaseModel):
    name:     str | None             = Field(default=None, min_length=1, max_length=255)
    settings: dict | None            = Field(default=None)


# ── Responses ──────────────────────────────────────────────────

class UserResponse(BaseModel):
    id:             str
    org_id:         str
    email:          str
    full_name:      str
    role:           str
    mfa_enabled:    bool
    email_verified: bool
    is_active:      bool
    last_login_at:  datetime | None = None
    created_at:     datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items:  list[UserResponse]
    total:  int
    limit:  int
    offset: int


class OrgResponse(BaseModel):
    id:                   str
    name:                 str
    slug:                 str
    plan_tier:            str
    max_assets:           int
    max_users:            int
    max_concurrent_scans: int
    is_active:            bool
    created_at:           datetime

    model_config = {"from_attributes": True}
