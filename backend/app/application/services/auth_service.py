"""
Authentication service — orchestrates all auth flows.

Responsibilities (single service, multiple use-cases):
  - register(...)       create org + owner user in one transaction
  - login(...)          verify credentials, issue token pair
  - refresh(...)        rotate refresh token, issue new access token
  - logout(...)         revoke refresh token
  - change_password(...) verify old password, update hash, revoke all sessions

What this service does NOT do:
  - HTTP — no Request/Response objects, no status codes
  - DB schema — delegates all persistence to repositories
  - Token encoding — delegates to JWTHandler
  - Hashing — delegates to PasswordHandler

Password policy (enforced here, not in Pydantic schema):
  - Minimum 8 characters
  - At least one uppercase, one digit
"""
from __future__ import annotations

import re

import structlog

from app.application.dto.auth_dto import (
    AuthenticatedUser,
    ChangePasswordInput,
    LoginInput,
    OrganizationDTO,
    RefreshInput,
    RegisterInput,
    TokenPair,
    UserDTO,
)
from app.domain.enums import AuditAction, PlanTier, UserRole
from app.domain.exceptions import (
    AuthenticationError,
    InvalidTokenError,
    PlanLimitError,
    ResourceConflictError,
    ResourceNotFoundError,
    TokenExpiredError,
    ValidationError,
)
from app.infrastructure.database.repositories.organization_repository import (
    OrganizationRepository,
)
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.audit_logger import AuditLogger
from app.infrastructure.security.jwt_handler import JWTHandler
from app.infrastructure.security.password_handler import PasswordHandler

logger = structlog.get_logger(__name__)

_PASSWORD_RE = re.compile(r"^(?=.*[A-Z])(?=.*\d).{8,}$")


def _validate_password(password: str) -> None:
    if not _PASSWORD_RE.match(password):
        raise ValidationError(
            "password",
            "Must be at least 8 characters and contain an uppercase letter and a digit",
        )


def _user_to_dto(user: object) -> UserDTO:  # type: ignore[return]
    from app.infrastructure.database.models import UserModel
    u: UserModel = user  # type: ignore[assignment]
    return UserDTO(
        id=u.id,
        org_id=u.organization_id,
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        mfa_enabled=u.mfa_enabled,
        is_active=u.is_active,
        email_verified=u.email_verified,
        last_login_at=u.last_login_at,
        created_at=u.created_at,
    )


def _org_to_dto(org: object) -> OrganizationDTO:  # type: ignore[return]
    from app.infrastructure.database.models import OrganizationModel
    o: OrganizationModel = org  # type: ignore[assignment]
    return OrganizationDTO(
        id=o.id,
        name=o.name,
        slug=o.slug,
        plan_tier=o.plan_tier,
        max_assets=o.max_assets,
        max_users=o.max_users,
        max_concurrent_scans=o.max_concurrent_scans,
        is_active=o.is_active,
        created_at=o.created_at,
    )


class AuthService:

    def __init__(
        self,
        user_repo: UserRepository,
        org_repo: OrganizationRepository,
        password_handler: PasswordHandler,
        jwt_handler: JWTHandler,
        audit: AuditLogger,
    ) -> None:
        self._users    = user_repo
        self._orgs     = org_repo
        self._pw       = password_handler
        self._jwt      = jwt_handler
        self._audit    = audit

    # ── Registration ───────────────────────────────────────────

    async def register(self, inp: RegisterInput) -> tuple[UserDTO, OrganizationDTO]:
        """
        Create a new organisation and its first owner user atomically.
        Both are flushed in the same transaction — the session is committed
        by the FastAPI DI session wrapper after this method returns.
        """
        _validate_password(inp.password)

        # Guard: email globally unique
        if await self._users.email_exists(inp.email):
            raise ResourceConflictError("User", "email", inp.email)

        # Guard: slug globally unique
        if await self._orgs.slug_exists(inp.organization_slug):
            raise ResourceConflictError("Organization", "slug", inp.organization_slug)

        # Validate slug format
        if not re.match(r"^[a-z0-9][a-z0-9\-]{2,61}[a-z0-9]$", inp.organization_slug):
            raise ValidationError(
                "organization_slug",
                "Must be 4-63 chars, lowercase alphanumeric and hyphens, "
                "not starting or ending with a hyphen",
            )

        plan = PlanTier.FREE
        org = await self._orgs.create(
            {
                "name": inp.organization_name.strip(),
                "slug": inp.organization_slug,
                "plan_tier": plan.value,
                "max_assets": plan.max_assets,
                "max_users": plan.max_users,
                "max_concurrent_scans": plan.max_concurrent_scans,
            }
        )

        user = await self._users.create(
            {
                "organization_id": org.id,
                "email": inp.email,
                "password_hash": self._pw.hash(inp.password),
                "full_name": inp.full_name.strip(),
                "role": UserRole.OWNER.value,
            }
        )

        await self._audit.log(
            AuditAction.ORG_CREATED,
            org_id=org.id,
            user_id=user.id,
            resource_type="organization",
            resource_id=org.id,
        )
        await self._audit.log(
            AuditAction.USER_CREATED,
            org_id=org.id,
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
        )

        logger.info("registration_complete", user_id=user.id, org_id=org.id)
        return _user_to_dto(user), _org_to_dto(org)

    # ── Login ──────────────────────────────────────────────────

    async def login(self, inp: LoginInput) -> TokenPair:
        """
        Verify credentials and issue a new token pair.

        Security: we call verify() regardless of whether the user exists
        to avoid timing-based user enumeration attacks.
        """
        user = await self._users.get_by_email(inp.email)
        # This is a validly formatted bcrypt hash (length 60) used to prevent timing attacks
        dummy_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKY.3p9b5tYnU6O"
        stored_hash = user.password_hash if user else dummy_hash

        password_ok = self._pw.verify(inp.password, stored_hash)

        if not user or not password_ok or not user.is_active:
            await self._audit.log(
                AuditAction.LOGIN_FAILED,
                payload={"email": inp.email, "ip": inp.ip_address},
            )
            raise AuthenticationError("Invalid email or password")

        # Silently upgrade weak bcrypt hashes on successful login
        if self._pw.needs_rehash(user.password_hash):
            await self._users.update_password(
                user.id, user.organization_id, self._pw.hash(inp.password)
            )

        tokens = await self._issue_token_pair(
            user_id=user.id,
            org_id=user.organization_id,
            role=user.role,
            email=user.email,
            ip_address=inp.ip_address,
            user_agent=inp.user_agent,
        )

        await self._users.update_last_login(user.id)

        await self._audit.log(
            AuditAction.LOGIN,
            org_id=user.organization_id,
            user_id=user.id,
            ip_address=inp.ip_address,
            user_agent=inp.user_agent,
        )

        return tokens

    # ── Token refresh ──────────────────────────────────────────

    async def refresh(self, inp: RefreshInput) -> TokenPair:
        """
        Rotate refresh token — revoke old, issue new pair.
        Rotation means a stolen token can only be used once before invalidation.
        """
        token_hash = self._jwt.hash_refresh_token(inp.refresh_token)
        stored     = await self._users.get_refresh_token_by_hash(token_hash)

        if stored is None:
            raise InvalidTokenError("Refresh token is invalid or expired")

        user = await self._users.get_by_id(stored.user_id, stored.user.organization_id if hasattr(stored, 'user') and stored.user else "")

        # Fallback: look up user by ID only
        if user is None:
            from sqlalchemy import select as sa_select
            from app.infrastructure.database.models import UserModel
            result = await self._users._s.execute(
                sa_select(UserModel).where(UserModel.id == stored.user_id)
            )
            user = result.scalar_one_or_none()

        if not user or not user.is_active:
            await self._users.revoke_refresh_token(token_hash)
            raise InvalidTokenError("User account is inactive")

        # Revoke old token before issuing new one — atomic rotation
        await self._users.revoke_refresh_token(token_hash)

        tokens = await self._issue_token_pair(
            user_id=user.id,
            org_id=user.organization_id,
            role=user.role,
            email=user.email,
            ip_address=inp.ip_address,
            user_agent=inp.user_agent,
        )

        await self._audit.log(
            AuditAction.TOKEN_REFRESH,
            org_id=user.organization_id,
            user_id=user.id,
            ip_address=inp.ip_address,
        )

        return tokens

    # ── Logout ─────────────────────────────────────────────────

    async def logout(
        self,
        refresh_token: str,
        current_user: AuthenticatedUser,
    ) -> None:
        """Revoke the presented refresh token."""
        token_hash = self._jwt.hash_refresh_token(refresh_token)
        await self._users.revoke_refresh_token(token_hash)
        await self._audit.log(
            AuditAction.LOGOUT,
            org_id=current_user.org_id,
            user_id=current_user.user_id,
        )

    # ── Change password ────────────────────────────────────────

    async def change_password(self, inp: ChangePasswordInput) -> None:
        """Verify old password, update hash, revoke ALL sessions."""
        user = await self._users.get_by_id(inp.user_id, inp.org_id)
        if user is None:
            raise ResourceNotFoundError("User", inp.user_id)

        if not self._pw.verify(inp.current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")

        _validate_password(inp.new_password)

        new_hash = self._pw.hash(inp.new_password)
        await self._users.update_password(inp.user_id, inp.org_id, new_hash)
        await self._users.revoke_all_refresh_tokens(inp.user_id)

        await self._audit.log(
            AuditAction.PASSWORD_CHANGED,
            org_id=inp.org_id,
            user_id=inp.user_id,
        )

    # ── Private helpers ────────────────────────────────────────

    async def _issue_token_pair(
        self,
        user_id: str,
        org_id: str,
        role: str,
        email: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> TokenPair:
        access = self._jwt.create_access_token(
            user_id=user_id,
            org_id=org_id,
            role=role,
            email=email,
        )
        raw_refresh, refresh_hash = self._jwt.create_refresh_token()
        expires_at = self._jwt.refresh_token_expires_at()

        await self._users.store_refresh_token(
            user_id=user_id,
            token_hash=refresh_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return TokenPair(access_token=access, refresh_token=raw_refresh)
