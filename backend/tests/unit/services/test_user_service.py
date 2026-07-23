"""
Unit tests for UserService.
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.user_service import UserService
from app.domain.enums import UserRole
from app.domain.exceptions import (
    AuthorizationError,
    InsufficientRoleError,
    ResourceNotFoundError,
    ValidationError,
)

# ── Helpers ────────────────────────────────────────────────────

def _make_user(
    *,
    user_id: str = "user-1",
    org_id: str = "org-1",
    email: str = "alice@example.com",
    full_name: str = "Alice",
    role: str = UserRole.OWNER.value,
    is_active: bool = True,
) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.organization_id = org_id
    u.email = email
    u.full_name = full_name
    u.role = role
    u.is_active = is_active
    u.mfa_enabled = False
    u.email_verified = False
    u.last_login_at = None
    u.created_at = datetime.now(UTC)
    return u


def _make_service(
    users: list[MagicMock] | None = None,
) -> tuple[UserService, AsyncMock, AsyncMock, AsyncMock]:
    user_repo = AsyncMock()
    org_repo  = AsyncMock()
    audit     = AsyncMock()

    default_users = users or [_make_user()]

    async def _list_by_org(org_id, limit=50, offset=0):
        return default_users, len(default_users)

    user_repo.get_by_id.return_value = default_users[0] if default_users else None
    user_repo.list_by_org.side_effect = _list_by_org

    svc = UserService(user_repo=user_repo, org_repo=org_repo, audit=audit)
    return svc, user_repo, org_repo, audit


# ══════════════════════════════════════════════════════════════════
# get_user()
# ══════════════════════════════════════════════════════════════════

class TestGetUser:

    @pytest.mark.asyncio
    async def test_returns_dto_for_existing_user(self):
        user = _make_user()
        svc, user_repo, *_ = _make_service([user])
        user_repo.get_by_id.return_value = user

        dto = await svc.get_user("user-1", "org-1")

        assert dto.id == "user-1"
        assert dto.email == "alice@example.com"

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_user(self):
        svc, user_repo, *_ = _make_service()
        user_repo.get_by_id.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await svc.get_user("ghost", "org-1")
        assert exc_info.value.resource_type == "User"


# ══════════════════════════════════════════════════════════════════
# update_profile()
# ══════════════════════════════════════════════════════════════════

class TestUpdateProfile:

    @pytest.mark.asyncio
    async def test_updates_full_name(self):
        user = _make_user()
        updated = _make_user(full_name="Alice Updated")
        svc, user_repo, *_ = _make_service([user])
        user_repo.update.return_value = updated

        dto = await svc.update_profile("user-1", "org-1", full_name="Alice Updated")

        user_repo.update.assert_called_once()
        assert dto.full_name == "Alice Updated"

    @pytest.mark.asyncio
    async def test_blank_name_raises_validation_error(self):
        svc, *_ = _make_service()

        with pytest.raises(ValidationError) as exc_info:
            await svc.update_profile("user-1", "org-1", full_name="   ")
        assert "full_name" in exc_info.value.field

    @pytest.mark.asyncio
    async def test_no_fields_is_noop(self):
        user = _make_user()
        svc, user_repo, *_ = _make_service([user])

        dto = await svc.update_profile("user-1", "org-1")

        user_repo.update.assert_not_called()
        assert dto.id == user.id

    @pytest.mark.asyncio
    async def test_name_too_long_raises_validation_error(self):
        svc, *_ = _make_service()
        with pytest.raises(ValidationError):
            await svc.update_profile("user-1", "org-1", full_name="x" * 256)


# ══════════════════════════════════════════════════════════════════
# change_role()
# ══════════════════════════════════════════════════════════════════

class TestChangeRole:

    @pytest.mark.asyncio
    async def test_owner_can_promote_viewer_to_analyst(self):
        owner   = _make_user(user_id="owner-1", role=UserRole.OWNER.value)
        analyst = _make_user(user_id="user-2",  role=UserRole.VIEWER.value)
        svc, user_repo, *_ = _make_service([owner, analyst])
        user_repo.get_by_id.return_value = analyst
        updated = _make_user(user_id="user-2", role=UserRole.ANALYST.value)
        user_repo.update.return_value = updated

        dto = await svc.change_role(
            target_user_id="user-2",
            new_role=UserRole.ANALYST,
            org_id="org-1",
            acting_user_id="owner-1",
            acting_role=UserRole.OWNER,
        )

        assert dto.role == UserRole.ANALYST.value

    @pytest.mark.asyncio
    async def test_non_owner_cannot_change_roles(self):
        svc, *_ = _make_service()

        with pytest.raises(InsufficientRoleError):
            await svc.change_role(
                target_user_id="user-2",
                new_role=UserRole.ANALYST,
                org_id="org-1",
                acting_user_id="user-1",
                acting_role=UserRole.ANALYST,  # not owner
            )

    @pytest.mark.asyncio
    async def test_cannot_change_own_role(self):
        svc, *_ = _make_service()

        with pytest.raises(AuthorizationError):
            await svc.change_role(
                target_user_id="user-1",   # same as acting_user_id
                new_role=UserRole.ANALYST,
                org_id="org-1",
                acting_user_id="user-1",
                acting_role=UserRole.OWNER,
            )

    @pytest.mark.asyncio
    async def test_cannot_promote_to_owner(self):
        svc, *_ = _make_service()

        with pytest.raises(AuthorizationError) as exc_info:
            await svc.change_role(
                target_user_id="user-2",
                new_role=UserRole.OWNER,   # forbidden via API
                org_id="org-1",
                acting_user_id="user-1",
                acting_role=UserRole.OWNER,
            )
        assert "OWNER" in str(exc_info.value.message).upper() or \
               "owner" in str(exc_info.value.message).lower()


# ══════════════════════════════════════════════════════════════════
# deactivate_user()
# ══════════════════════════════════════════════════════════════════

class TestDeactivateUser:

    @pytest.mark.asyncio
    async def test_admin_can_deactivate_analyst(self):
        admin   = _make_user(user_id="admin-1", role=UserRole.ADMIN.value)
        analyst = _make_user(user_id="user-2",  role=UserRole.ANALYST.value)
        svc, user_repo, *_ = _make_service([admin, analyst])
        user_repo.get_by_id.return_value = analyst

        await svc.deactivate_user(
            target_user_id="user-2",
            org_id="org-1",
            acting_user_id="admin-1",
            acting_role=UserRole.ADMIN,
        )

        user_repo.deactivate.assert_called_once_with("user-2", "org-1")

    @pytest.mark.asyncio
    async def test_analyst_cannot_deactivate_anyone(self):
        svc, *_ = _make_service()

        with pytest.raises(InsufficientRoleError):
            await svc.deactivate_user(
                target_user_id="user-2",
                org_id="org-1",
                acting_user_id="user-1",
                acting_role=UserRole.ANALYST,
            )

    @pytest.mark.asyncio
    async def test_cannot_deactivate_self(self):
        svc, *_ = _make_service()

        with pytest.raises(AuthorizationError):
            await svc.deactivate_user(
                target_user_id="user-1",   # same as acting
                org_id="org-1",
                acting_user_id="user-1",
                acting_role=UserRole.ADMIN,
            )

    @pytest.mark.asyncio
    async def test_cannot_deactivate_last_owner(self):
        owner = _make_user(user_id="owner-1", role=UserRole.OWNER.value)
        svc, user_repo, *_ = _make_service([owner])
        user_repo.get_by_id.return_value = owner

        with pytest.raises(AuthorizationError) as exc_info:
            await svc.deactivate_user(
                target_user_id="owner-1",
                org_id="org-1",
                acting_user_id="admin-1",
                acting_role=UserRole.ADMIN,
            )
        assert "last owner" in str(exc_info.value.message).lower()
