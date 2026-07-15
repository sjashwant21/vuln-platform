"""
Organization (tenant) management service.

Handles:
  - Fetching org details for the authenticated tenant
  - Updating org settings (admin-only)
  - Plan-tier enforcement helper (used by other services)
"""
from __future__ import annotations

import structlog

from app.application.dto.auth_dto import OrganizationDTO
from app.domain.enums import AuditAction, PlanTier, UserRole
from app.domain.exceptions import (
    InsufficientRoleError,
    ResourceNotFoundError,
    ValidationError,
)
from app.infrastructure.database.repositories.organization_repository import (
    OrganizationRepository,
)
from app.infrastructure.security.audit_logger import AuditLogger

logger = structlog.get_logger(__name__)


def _to_dto(org: object) -> OrganizationDTO:
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


class OrganizationService:

    def __init__(
        self,
        org_repo: OrganizationRepository,
        audit: AuditLogger,
    ) -> None:
        self._orgs  = org_repo
        self._audit = audit

    # ── Queries ────────────────────────────────────────────────

    async def get_org(self, org_id: str) -> OrganizationDTO:
        org = await self._orgs.get_by_id(org_id)
        if org is None:
            raise ResourceNotFoundError("Organization", org_id)
        return _to_dto(org)

    # ── Updates ────────────────────────────────────────────────

    async def update_org(
        self,
        org_id: str,
        acting_role: UserRole,
        acting_user_id: str,
        name: str | None = None,
        settings: dict | None = None,
    ) -> OrganizationDTO:
        """Only ADMIN and above may update org details."""
        if not acting_role.is_admin_or_above():
            raise InsufficientRoleError(
                required=UserRole.ADMIN.value,
                current=acting_role.value,
            )

        updates: dict[str, object] = {}

        if name is not None:
            name = name.strip()
            if not name:
                raise ValidationError("name", "Organisation name cannot be blank")
            if len(name) > 255:
                raise ValidationError("name", "Name must be 255 characters or fewer")
            updates["name"] = name

        if settings is not None:
            updates["settings"] = settings

        if not updates:
            return await self.get_org(org_id)

        updated = await self._orgs.update(org_id, updates)
        if updated is None:
            raise ResourceNotFoundError("Organization", org_id)

        await self._audit.log(
            AuditAction.ORG_UPDATED,
            org_id=org_id,
            user_id=acting_user_id,
            resource_type="organization",
            resource_id=org_id,
            payload={"fields": list(updates.keys())},
        )

        return _to_dto(updated)

    # ── Plan enforcement ───────────────────────────────────────

    async def check_asset_limit(self, org_id: str, current_count: int) -> None:
        """
        Raise PlanLimitError if adding one more asset would exceed the plan limit.
        Called by AssetService before creating new assets.
        """
        from app.domain.exceptions import PlanLimitError

        org = await self._orgs.get_by_id(org_id)
        if org is None:
            raise ResourceNotFoundError("Organization", org_id)

        if current_count >= org.max_assets:
            raise PlanLimitError(
                feature="assets",
                limit=org.max_assets,
                current=current_count,
            )

    async def check_user_limit(self, org_id: str, current_count: int) -> None:
        """Raise PlanLimitError if inviting one more user would exceed the plan limit."""
        from app.domain.exceptions import PlanLimitError

        org = await self._orgs.get_by_id(org_id)
        if org is None:
            raise ResourceNotFoundError("Organization", org_id)

        if current_count >= org.max_users:
            raise PlanLimitError(
                feature="users",
                limit=org.max_users,
                current=current_count,
            )
