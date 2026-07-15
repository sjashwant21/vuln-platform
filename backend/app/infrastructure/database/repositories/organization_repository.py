"""
Organization (tenant) repository — SQLAlchemy 2.0 async implementation.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import OrganizationModel

logger = structlog.get_logger(__name__)


class OrganizationRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── Lookups ────────────────────────────────────────────────

    async def get_by_id(self, org_id: str) -> OrganizationModel | None:
        stmt = select(OrganizationModel).where(
            and_(
                OrganizationModel.id == org_id,
                OrganizationModel.is_active.is_(True),
            )
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> OrganizationModel | None:
        stmt = select(OrganizationModel).where(
            and_(
                OrganizationModel.slug == slug.lower().strip(),
                OrganizationModel.is_active.is_(True),
            )
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        stmt = select(func.count()).select_from(OrganizationModel).where(
            OrganizationModel.slug == slug.lower().strip()
        )
        return (await self._s.execute(stmt)).scalar_one() > 0

    async def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OrganizationModel], int]:
        """Super-admin usage only — not exposed to tenant users."""
        base = OrganizationModel.is_active.is_(True)
        total = (
            await self._s.execute(
                select(func.count()).select_from(OrganizationModel).where(base)
            )
        ).scalar_one()
        rows = (
            await self._s.execute(
                select(OrganizationModel)
                .where(base)
                .order_by(OrganizationModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()
        return list(rows), total

    # ── Mutations ──────────────────────────────────────────────

    async def create(self, data: dict[str, Any]) -> OrganizationModel:
        org = OrganizationModel(
            id=str(uuid.uuid4()),
            **{**data, "slug": data["slug"].lower().strip()},
        )
        self._s.add(org)
        await self._s.flush()
        await self._s.refresh(org)
        logger.info("org_created", org_id=org.id, slug=org.slug)
        return org

    async def update(
        self,
        org_id: str,
        data: dict[str, Any],
    ) -> OrganizationModel | None:
        stmt = (
            update(OrganizationModel)
            .where(OrganizationModel.id == org_id)
            .values(**data, updated_at=datetime.now(UTC))
            .returning(OrganizationModel)
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def update_plan(
        self,
        org_id: str,
        plan_tier: str,
        max_assets: int,
        max_users: int,
        max_concurrent_scans: int,
    ) -> OrganizationModel | None:
        return await self.update(
            org_id,
            {
                "plan_tier": plan_tier,
                "max_assets": max_assets,
                "max_users": max_users,
                "max_concurrent_scans": max_concurrent_scans,
            },
        )

    async def deactivate(self, org_id: str) -> bool:
        stmt = (
            update(OrganizationModel)
            .where(OrganizationModel.id == org_id)
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        result = await self._s.execute(stmt)
        return result.rowcount > 0
