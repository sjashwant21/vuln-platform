"""Asset service layer."""

from __future__ import annotations

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.asset_schemas import AssetCreateRequest, AssetUpdateRequest
from app.domain.exceptions import ResourceNotFoundError
from app.infrastructure.database.models import AssetModel


class AssetService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_assets(
        self, org_id: str, limit: int = 50, offset: int = 0, criticality: str | None = None, search: str | None = None
    ) -> tuple[list[AssetModel], int]:
        stmt = select(AssetModel).where(AssetModel.organization_id == org_id)

        if criticality:
            stmt = stmt.where(AssetModel.criticality == criticality)

        if search:
            stmt = stmt.where(
                or_(
                    AssetModel.hostname.ilike(f"%{search}%"),
                    AssetModel.ip_address.ilike(f"%{search}%"),
                )
            )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._s.execute(count_stmt)).scalar() or 0

        # Get paginated items
        stmt = stmt.order_by(AssetModel.created_at.desc()).limit(limit).offset(offset)
        stmt = stmt.options(selectinload(AssetModel.ports))
        items = (await self._s.execute(stmt)).scalars().all()

        return list(items), total

    async def get_asset(self, org_id: str, asset_id: str) -> AssetModel:
        stmt = (
            select(AssetModel)
            .where(and_(AssetModel.id == asset_id, AssetModel.organization_id == org_id))
            .options(selectinload(AssetModel.ports))
        )
        asset = (await self._s.execute(stmt)).scalar_one_or_none()
        if not asset:
            raise ResourceNotFoundError(f"Asset {asset_id} not found")
        return asset

    async def create_asset(self, org_id: str, data: AssetCreateRequest) -> AssetModel:
        asset = AssetModel(
            organization_id=org_id,
            hostname=data.hostname,
            ip_address=data.ip_address,
            asset_type=data.asset_type,
            os_fingerprint=data.os_fingerprint,
            criticality=data.criticality,
            tags=data.tags,
            is_active=data.is_active,
        )
        self._s.add(asset)
        await self._s.commit()
        await self._s.refresh(asset)
        return asset

    async def update_asset(self, org_id: str, asset_id: str, data: AssetUpdateRequest) -> AssetModel:
        asset = await self.get_asset(org_id, asset_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(asset, key, value)

        await self._s.commit()
        await self._s.refresh(asset)
        return asset

    async def delete_asset(self, org_id: str, asset_id: str) -> None:
        asset = await self.get_asset(org_id, asset_id)
        await self._s.delete(asset)
        await self._s.commit()
