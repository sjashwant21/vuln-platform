"""
Unit tests for AuthService.

All external dependencies (repos, JWT handler, password handler, audit)
are replaced with AsyncMock / MagicMock so these tests run without a DB
and complete in milliseconds.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.dto.auth_dto import (
    ChangePasswordInput,
    LoginInput,
    RefreshInput,
    RegisterInput,
)
from app.application.services.auth_service import AuthService
from app.domain.enums import UserRole
from app.domain.exceptions import (
    AuthenticationError,
    InvalidTokenError,
    ResourceConflictError,
    ValidationError,
)

# ── Helpers ────────────────────────────────────────────────────

def _make_user(
    *,
    user_id: str = "user-1",
    org_id: str = "org-1",
    email: str = "alice@example.com",
    role: str = UserRole.OWNER.value,
    is_active: bool = True,
    password_hash: str = "$2b$12$fakehashXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.organization_id = org_id
    user.email = email
    user.role = role
    user.is_active = is_active
    user.password_hash = password_hash
    user.mfa_enabled = False
    user.email_verified = False
    user.full_name = "Alice"
    user.last_login_at = None
    user.created_at = datetime.now(UTC)
    return user


def _make_org(
    *,
    org_id: str = "org-1",
    slug: str = "acme",
) -> MagicMock:
    org = MagicMock()
    org.id = org_id
    org.name = "Acme"
    org.slug = slug
    org.plan_tier = "free"
    org.max_assets = 5
    org.max_users = 2
    org.max_concurrent_scans = 1
    org.is_active = True
    org.created_at = datetime.now(UTC)
    return org


def _make_service(
    *,
    user: MagicMock | None = None,
    org: MagicMock | None = None,
    email_exists: bool = False,
    slug_exists: bool = False,
    pw_verify: bool = True,
    pw_needs_rehash: bool = False,
) -> tuple[AuthService, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
    user_repo = AsyncMock()
    org_repo  = AsyncMock()
    pw        = MagicMock()
    jwt       = MagicMock()
    audit     = AsyncMock()

    # Default stubs
    user_repo.email_exists.return_value  = email_exists
    user_repo.get_by_email.return_value  = user
    user_repo.create.return_value        = user or _make_user()
    user_repo.get_refresh_token_by_hash.return_value = None

    org_repo.slug_exists.return_value = slug_exists
    org_repo.create.return_value      = org or _make_org()

    pw.hash.return_value         = "$2b$12$newhashXXXXXXXXXXXXXXXXXXXXXXX"
    pw.verify.return_value       = pw_verify
    pw.needs_rehash.return_value = pw_needs_rehash

    jwt.create_access_token.return_value    = "access.token.here"
    jwt.create_refresh_token.return_value   = ("raw-refresh", "hashed-refresh")
    jwt.hash_refresh_token.return_value     = "hashed-refresh"
    jwt.refresh_token_expires_at.return_value = datetime.now(UTC) + timedelta(days=7)

    svc = AuthService(
        user_repo=user_repo,
        org_repo=org_repo,
        password_handler=pw,
        jwt_handler=jwt,
        audit=audit,
    )
    return svc, user_repo, org_repo, pw, jwt, audit


# ══════════════════════════════════════════════════════════════════
# register()
# ══════════════════════════════════════════════════════════════════

class TestRegister:

    @pytest.mark.asyncio
    async def test_success_creates_org_and_user(self):
        svc, user_repo, org_repo, *_ = _make_service()

        user_dto, org_dto = await svc.register(
            RegisterInput(
                email="alice@example.com",
                password="Secure123",
                full_name="Alice",
                organization_name="Acme",
                organization_slug="acme-corp",
            )
        )

        org_repo.create.assert_called_once()
        user_repo.create.assert_called_once()
        assert user_dto.role == UserRole.OWNER.value
        assert org_dto.plan_tier == "free"

    @pytest.mark.asyncio
    async def test_duplicate_email_raises_conflict(self):
        svc, *_ = _make_service(email_exists=True)

        with pytest.raises(ResourceConflictError) as exc_info:
            await svc.register(
                RegisterInput(
                    email="alice@example.com",
                    password="Secure123",
                    full_name="Alice",
                    organization_name="Acme",
                    organization_slug="acme-corp",
                )
            )
        assert "email" in exc_info.value.field

    @pytest.mark.asyncio
    async def test_duplicate_slug_raises_conflict(self):
        svc, *_ = _make_service(slug_exists=True)

        with pytest.raises(ResourceConflictError) as exc_info:
            await svc.register(
                RegisterInput(
                    email="alice@example.com",
                    password="Secure123",
                    full_name="Alice",
                    organization_name="Acme",
                    organization_slug="acme-corp",
                )
            )
        assert "slug" in exc_info.value.field

    @pytest.mark.asyncio
    async def test_weak_password_raises_validation_error(self):
        svc, *_ = _make_service()

        with pytest.raises(ValidationError) as exc_info:
            await svc.register(
                RegisterInput(
                    email="alice@example.com",
                    password="weak",           # no uppercase, no digit, < 8 chars
                    full_name="Alice",
                    organization_name="Acme",
                    organization_slug="acme-corp",
                )
            )
        assert "password" in exc_info.value.field

    @pytest.mark.asyncio
    async def test_password_no_uppercase_rejected(self):
        svc, *_ = _make_service()
        with pytest.raises(ValidationError):
            await svc.register(
                RegisterInput(
                    email="alice@example.com",
                    password="nouppercase1",
                    full_name="Alice",
                    organization_name="Acme",
                    organization_slug="acme-corp",
                )
            )

    @pytest.mark.asyncio
    async def test_password_no_digit_rejected(self):
        svc, *_ = _make_service()
        with pytest.raises(ValidationError):
            await svc.register(
                RegisterInput(
                    email="alice@example.com",
                    password="NoDigitsHere",
                    full_name="Alice",
                    organization_name="Acme",
                    organization_slug="acme-corp",
                )
            )

    @pytest.mark.asyncio
    async def test_invalid_slug_format_raises_validation_error(self):
        svc, *_ = _make_service()
        with pytest.raises(ValidationError) as exc_info:
            await svc.register(
                RegisterInput(
                    email="alice@example.com",
                    password="Secure123",
                    full_name="Alice",
                    organization_name="Acme",
                    organization_slug="UPPER_CASE",  # invalid
                )
            )
        assert "slug" in exc_info.value.field

    @pytest.mark.asyncio
    async def test_audit_events_logged_on_success(self):
        svc, _, _, _, _, audit = _make_service()
        await svc.register(
            RegisterInput(
                email="alice@example.com",
                password="Secure123",
                full_name="Alice",
                organization_name="Acme",
                organization_slug="acme-corp",
            )
        )
        # org.created + user.created = 2 audit events
        assert audit.log.call_count == 2


# ══════════════════════════════════════════════════════════════════
# login()
# ══════════════════════════════════════════════════════════════════

class TestLogin:

    @pytest.mark.asyncio
    async def test_success_returns_token_pair(self):
        user = _make_user()
        svc, *_ = _make_service(user=user, pw_verify=True)

        tokens = await svc.login(
            LoginInput(email="alice@example.com", password="Secure123")
        )

        assert tokens.access_token == "access.token.here"
        assert tokens.refresh_token == "raw-refresh"
        assert tokens.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_wrong_password_raises_auth_error(self):
        user = _make_user()
        svc, *_ = _make_service(user=user, pw_verify=False)

        with pytest.raises(AuthenticationError):
            await svc.login(
                LoginInput(email="alice@example.com", password="WrongPassword1")
            )

    @pytest.mark.asyncio
    async def test_nonexistent_user_raises_auth_error(self):
        """
        Even when user doesn't exist, verify() is still called with a dummy hash
        to prevent timing attacks.
        """
        svc, user_repo, *_ = _make_service(user=None, pw_verify=False)
        user_repo.get_by_email.return_value = None

        with pytest.raises(AuthenticationError):
            await svc.login(
                LoginInput(email="nobody@example.com", password="Secure123")
            )

    @pytest.mark.asyncio
    async def test_inactive_user_raises_auth_error(self):
        user = _make_user(is_active=False)
        svc, *_ = _make_service(user=user, pw_verify=True)

        with pytest.raises(AuthenticationError):
            await svc.login(
                LoginInput(email="alice@example.com", password="Secure123")
            )

    @pytest.mark.asyncio
    async def test_failed_login_writes_audit_log(self):
        svc, user_repo, _, _, _, audit = _make_service(user=None, pw_verify=False)
        user_repo.get_by_email.return_value = None

        with pytest.raises(AuthenticationError):
            await svc.login(
                LoginInput(
                    email="nobody@example.com",
                    password="Secure123",
                    ip_address="1.2.3.4",
                )
            )

        audit.log.assert_called_once()
        call_kwargs = audit.log.call_args
        from app.domain.enums import AuditAction
        assert call_kwargs[0][0] == AuditAction.LOGIN_FAILED

    @pytest.mark.asyncio
    async def test_needs_rehash_updates_password(self):
        user = _make_user()
        svc, user_repo, _, pw, _, _ = _make_service(
            user=user, pw_verify=True, pw_needs_rehash=True
        )

        await svc.login(LoginInput(email="alice@example.com", password="Secure123"))

        user_repo.update_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_updates_last_login(self):
        user = _make_user()
        svc, user_repo, *_ = _make_service(user=user, pw_verify=True)

        await svc.login(LoginInput(email="alice@example.com", password="Secure123"))

        user_repo.update_last_login.assert_called_once_with(user.id)


# ══════════════════════════════════════════════════════════════════
# refresh()
# ══════════════════════════════════════════════════════════════════

class TestRefresh:

    @pytest.mark.asyncio
    async def test_invalid_token_raises_error(self):
        svc, user_repo, *_ = _make_service()
        user_repo.get_refresh_token_by_hash.return_value = None

        with pytest.raises(InvalidTokenError):
            await svc.refresh(RefreshInput(refresh_token="bad-token"))

    @pytest.mark.asyncio
    async def test_valid_token_revokes_old_and_issues_new(self):
        user = _make_user()

        stored_token = MagicMock()
        stored_token.user_id = user.id
        stored_token.user = user

        svc, user_repo, *_ = _make_service(user=user)
        user_repo.get_refresh_token_by_hash.return_value = stored_token

        tokens = await svc.refresh(RefreshInput(refresh_token="valid-raw-token"))

        user_repo.revoke_refresh_token.assert_called_once()
        user_repo.store_refresh_token.assert_called_once()
        assert tokens.access_token == "access.token.here"


# ══════════════════════════════════════════════════════════════════
# logout()
# ══════════════════════════════════════════════════════════════════

class TestLogout:

    @pytest.mark.asyncio
    async def test_logout_revokes_token(self):
        from app.application.dto.auth_dto import AuthenticatedUser
        user = _make_user()
        svc, user_repo, _, _, _, audit = _make_service(user=user)

        current = AuthenticatedUser(
            user_id=user.id,
            org_id=user.organization_id,
            role=user.role,
            email=user.email,
        )

        await svc.logout("raw-refresh-token", current)

        user_repo.revoke_refresh_token.assert_called_once()
        audit.log.assert_called_once()


# ══════════════════════════════════════════════════════════════════
# change_password()
# ══════════════════════════════════════════════════════════════════

class TestChangePassword:

    @pytest.mark.asyncio
    async def test_success_updates_hash_and_revokes_sessions(self):
        user = _make_user()
        svc, user_repo, *_ = _make_service(user=user, pw_verify=True)

        await svc.change_password(
            ChangePasswordInput(
                user_id=user.id,
                org_id=user.organization_id,
                current_password="OldSecure1",
                new_password="NewSecure2",
            )
        )

        user_repo.update_password.assert_called_once()
        user_repo.revoke_all_refresh_tokens.assert_called_once_with(user.id)

    @pytest.mark.asyncio
    async def test_wrong_current_password_raises_error(self):
        user = _make_user()
        svc, *_ = _make_service(user=user, pw_verify=False)

        with pytest.raises(AuthenticationError):
            await svc.change_password(
                ChangePasswordInput(
                    user_id=user.id,
                    org_id=user.organization_id,
                    current_password="WrongPass1",
                    new_password="NewSecure2",
                )
            )

    @pytest.mark.asyncio
    async def test_weak_new_password_raises_validation_error(self):
        user = _make_user()
        svc, *_ = _make_service(user=user, pw_verify=True)

        with pytest.raises(ValidationError):
            await svc.change_password(
                ChangePasswordInput(
                    user_id=user.id,
                    org_id=user.organization_id,
                    current_password="OldSecure1",
                    new_password="weak",
                )
            )
