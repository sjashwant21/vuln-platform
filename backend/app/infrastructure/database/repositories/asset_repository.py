"""
Asset repository - SQLAlchemy async implementation.
Enforces tenant isolation on every query via organization_id filter.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.interfaces.repositories import AssetRepository
from app.infrastructure.database.models import AssetModel, AssetPortModel

logger = structlog.get_logger(__name__)


class SQLAssetRepository(AssetRepository):
    """Async SQLAlchemy implementation of AssetRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, asset_id: str, org_id: str) -> AssetModel | None:
        """Fetch asset by ID, strictly scoped to the organization."""
        stmt = (
            select(AssetModel)
            .where(
                and_(
                    AssetModel.id == asset_id,
                    AssetModel.organization_id == org_id,
                    AssetModel.is_active == True,  # noqa: E712
                )
            )
            .options(selectinload(AssetModel.ports))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ip(self, ip_address: str, org_id: str) -> AssetModel | None:
        """Find an asset by IP address within an organization."""
        stmt = select(AssetModel).where(
            and_(
                AssetModel.ip_address == ip_address,
                AssetModel.organization_id == org_id,
                AssetModel.is_active == True,  # noqa: E712
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        org_id: str,
        limit: int,
        offset: int,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[AssetModel], int]:
        """
        Paginated list of assets for an organization.
        Returns (items, total_count) for pagination.
        """
        base_where = and_(
            AssetModel.organization_id == org_id,
            AssetModel.is_active == True,  # noqa: E712
        )

        # Apply optional filters
        conditions = [base_where]
        if filters:
            if criticality := filters.get("criticality"):
                conditions.append(AssetModel.criticality == criticality)
            if asset_type := filters.get("asset_type"):
                conditions.append(AssetModel.asset_type == asset_type)
            if search := filters.get("search"):
                conditions.append(
                    AssetModel.hostname.ilike(f"%{search}%")
                    | AssetModel.ip_address.ilike(f"%{search}%")
                )

        # Count query
        count_stmt = select(func.count()).select_from(AssetModel).where(and_(*conditions))
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Data query with eager-loaded ports
        data_stmt = (
            select(AssetModel)
            .where(and_(*conditions))
            .options(selectinload(AssetModel.ports))
            .order_by(AssetModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(data_stmt)
        items = list(result.scalars().all())

        return items, total

    async def create(self, data: dict[str, Any]) -> AssetModel:
        """Create a new asset."""
        asset = AssetModel(
            id=str(uuid.uuid4()),
            **data,
        )
        self._session.add(asset)
        await self._session.flush()  # Get ID without committing
        await self._session.refresh(asset)
        logger.info("asset_created", asset_id=asset.id, org_id=data.get("organization_id"))
        return asset

    async def update(
        self, asset_id: str, org_id: str, data: dict[str, Any]
    ) -> AssetModel | None:
        """Update asset fields, returning updated model."""
        stmt = (
            update(AssetModel)
            .where(
                and_(
                    AssetModel.id == asset_id,
                    AssetModel.organization_id == org_id,
                )
            )
            .values(**data, updated_at=datetime.now(UTC))
            .returning(AssetModel)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, asset_id: str, org_id: str) -> bool:
        """Soft delete - sets is_active=False."""
        stmt = (
            update(AssetModel)
            .where(
                and_(
                    AssetModel.id == asset_id,
                    AssetModel.organization_id == org_id,
                )
            )
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def upsert_port(self, asset_id: str, port_data: dict[str, Any]) -> AssetPortModel:
        """
        Insert or update a port record for an asset.
        Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE.
        """
        from sqlalchemy.dialects.postgresql import insert

        stmt = (
            insert(AssetPortModel)
            .values(
                id=str(uuid.uuid4()),
                asset_id=asset_id,
                **port_data,
                scanned_at=datetime.now(UTC),
            )
            .on_conflict_do_update(
                constraint="uq_asset_ports_asset_port_proto",
                set_={
                    "service": port_data.get("service"),
                    "service_version": port_data.get("service_version"),
                    "banner": port_data.get("banner"),
                    "state": port_data.get("state", "open"),
                    "scanned_at": datetime.now(UTC),
                },
            )
            .returning(AssetPortModel)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_by_org(self, org_id: str) -> int:
        """Count active assets in an organization."""
        stmt = select(func.count()).select_from(AssetModel).where(
            and_(
                AssetModel.organization_id == org_id,
                AssetModel.is_active == True,  # noqa: E712
            )
        )
        return (await self._session.execute(stmt)).scalar_one()
