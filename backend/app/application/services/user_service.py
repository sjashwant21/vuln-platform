"""
User management service.

Handles user lifecycle within an organisation:
  - profile reads
  - profile updates
  - role changes (owner-only)
  - deactivation

All operations are scoped to org_id — cross-tenant access is impossible.
"""
from __future__ import annotations

import structlog

from app.application.dto.auth_dto import UserDTO
from app.domain.enums import AuditAction, UserRole
from app.domain.exceptions import (
    AuthorizationError,
    InsufficientRoleError,
    ResourceNotFoundError,
    ValidationError,
)
from app.infrastructure.database.repositories.organization_repository import (
    OrganizationRepository,
)
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.security.audit_logger import AuditLogger

logger = structlog.get_logger(__name__)


def _to_dto(user: object) -> UserDTO:
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


class UserService:

    def __init__(
        self,
        user_repo: UserRepository,
        org_repo: OrganizationRepository,
        audit: AuditLogger,
    ) -> None:
        self._users = user_repo
        self._orgs  = org_repo
        self._audit = audit

    # ── Queries ────────────────────────────────────────────────

    async def get_user(self, user_id: str, org_id: str) -> UserDTO:
        user = await self._users.get_by_id(user_id, org_id)
        if user is None:
            raise ResourceNotFoundError("User", user_id)
        return _to_dto(user)

    async def list_users(
        self,
        org_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[UserDTO], int]:
        users, total = await self._users.list_by_org(org_id, limit, offset)
        return [_to_dto(u) for u in users], total

    # ── Profile update ─────────────────────────────────────────

    async def update_profile(
        self,
        user_id: str,
        org_id: str,
        full_name: str | None = None,
    ) -> UserDTO:
        """Users may only update their own profile fields."""
        updates: dict[str, object] = {}

        if full_name is not None:
            full_name = full_name.strip()
            if not full_name:
                raise ValidationError("full_name", "Name cannot be blank")
            if len(full_name) > 255:
                raise ValidationError("full_name", "Name must be 255 characters or fewer")
            updates["full_name"] = full_name

        if not updates:
            # No-op — return current state
            return await self.get_user(user_id, org_id)

        updated = await self._users.update(user_id, org_id, updates)
        if updated is None:
            raise ResourceNotFoundError("User", user_id)

        await self._audit.log(
            AuditAction.USER_UPDATED,
            org_id=org_id,
            user_id=user_id,
            resource_type="user",
            resource_id=user_id,
            payload={"fields": list(updates.keys())},
        )

        return _to_dto(updated)

    # ── Role management ────────────────────────────────────────

    async def change_role(
        self,
        target_user_id: str,
        new_role: UserRole,
        org_id: str,
        acting_user_id: str,
        acting_role: UserRole,
    ) -> UserDTO:
        """
        Change a member's role.

        Rules:
          - Only OWNER may change roles
          - Cannot demote yourself
          - Cannot promote to OWNER via API (prevents privilege escalation)
        """
        if not acting_role.is_owner():
            raise InsufficientRoleError(
                required=UserRole.OWNER.value,
                current=acting_role.value,
            )

        if target_user_id == acting_user_id:
            raise AuthorizationError("You cannot change your own role")

        if new_role == UserRole.OWNER:
            raise AuthorizationError(
                "Cannot promote to OWNER via API. "
                "Ownership transfer must go through the billing portal."
            )

        target = await self._users.get_by_id(target_user_id, org_id)
        if target is None:
            raise ResourceNotFoundError("User", target_user_id)

        old_role = target.role
        updated  = await self._users.update(
            target_user_id, org_id, {"role": new_role.value}
        )

        await self._audit.log(
            AuditAction.ROLE_CHANGED,
            org_id=org_id,
            user_id=acting_user_id,
            resource_type="user",
            resource_id=target_user_id,
            payload={"old_role": old_role, "new_role": new_role.value},
        )

        return _to_dto(updated)

    # ── Deactivation ───────────────────────────────────────────

    async def deactivate_user(
        self,
        target_user_id: str,
        org_id: str,
        acting_user_id: str,
        acting_role: UserRole,
    ) -> None:
        """
        Soft-delete a user (is_active=False).

        - OWNER and ADMIN may deactivate other members
        - Users may NOT deactivate themselves (use account-deletion flow)
        - Cannot deactivate the org's only OWNER
        """
        if not acting_role.is_admin_or_above():
            raise InsufficientRoleError(
                required=UserRole.ADMIN.value,
                current=acting_role.value,
            )

        if target_user_id == acting_user_id:
            raise AuthorizationError("You cannot deactivate your own account")

        target = await self._users.get_by_id(target_user_id, org_id)
        if target is None:
            raise ResourceNotFoundError("User", target_user_id)

        # Protect last owner
        if target.role == UserRole.OWNER.value:
            owners_count, _ = await self._users.list_by_org(org_id)
            owner_count = sum(1 for u in owners_count if u.role == UserRole.OWNER.value)
            if owner_count <= 1:
                raise AuthorizationError(
                    "Cannot deactivate the last owner of an organisation"
                )

        await self._users.deactivate(target_user_id, org_id)

        await self._audit.log(
            AuditAction.USER_DEACTIVATED,
            org_id=org_id,
            user_id=acting_user_id,
            resource_type="user",
            resource_id=target_user_id,
        )
