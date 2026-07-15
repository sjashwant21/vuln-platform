"""
Auth data transfer objects.

Plain dataclasses — no Pydantic, no ORM coupling.
These cross the service/API boundary carrying exactly what each side needs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RegisterInput:
    email: str
    password: str
    full_name: str
    organization_name: str
    organization_slug: str


@dataclass(frozen=True)
class LoginInput:
    email: str
    password: str
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900   # seconds (15 min)


@dataclass(frozen=True)
class RefreshInput:
    refresh_token: str
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class AuthenticatedUser:
    """Decoded JWT payload — injected into route handlers via DI."""
    user_id: str
    org_id: str
    role: str
    email: str


@dataclass(frozen=True)
class ChangePasswordInput:
    user_id: str
    org_id: str
    current_password: str
    new_password: str


@dataclass(frozen=True)
class MFASetupResult:
    secret: str
    provisioning_uri: str
    backup_codes: list[str]


@dataclass(frozen=True)
class UserDTO:
    id: str
    org_id: str
    email: str
    full_name: str
    role: str
    mfa_enabled: bool
    is_active: bool
    email_verified: bool
    last_login_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class OrganizationDTO:
    id: str
    name: str
    slug: str
    plan_tier: str
    max_assets: int
    max_users: int
    max_concurrent_scans: int
    is_active: bool
    created_at: datetime
