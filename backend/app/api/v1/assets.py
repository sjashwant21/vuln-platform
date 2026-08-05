from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.asset_schemas import (
    AssetCreateRequest,
    AssetDiscoverRequest,
    AssetListResponse,
    AssetResponse,
    AssetUpdateRequest,
)
from app.application.services.asset_service import AssetService
from app.dependencies import CurrentUser, get_db_session
from app.domain.exceptions import ResourceNotFoundError

router = APIRouter(prefix="/assets", tags=["Assets"])

DBSession = Annotated[AsyncSession, Depends(get_db_session)]


def _svc(db: DBSession) -> AssetService:
    return AssetService(db)


@router.get("", response_model=AssetListResponse, summary="List assets")
async def list_assets(
    current_user: CurrentUser,
    db: DBSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    criticality: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> AssetListResponse:
    """List all assets for the current organization."""
    items, total = await _svc(db).list_assets(
        org_id=current_user.org_id,
        limit=limit,
        offset=offset,
        criticality=criticality,
        search=search,
    )
    return AssetListResponse(
        items=[AssetResponse.model_validate(a) for a in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{asset_id}", response_model=AssetResponse, summary="Get asset details")
async def get_asset(asset_id: str, current_user: CurrentUser, db: DBSession) -> AssetResponse:
    try:
        asset = await _svc(db).get_asset(org_id=current_user.org_id, asset_id=asset_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return AssetResponse.model_validate(asset)


@router.post(
    "",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new asset",
)
async def create_asset(
    body: AssetCreateRequest, current_user: CurrentUser, db: DBSession
) -> AssetResponse:
    asset = await _svc(db).create_asset(org_id=current_user.org_id, data=body)
    return AssetResponse.model_validate(asset)


@router.patch("/{asset_id}", response_model=AssetResponse, summary="Update an asset")
async def update_asset(
    asset_id: str, body: AssetUpdateRequest, current_user: CurrentUser, db: DBSession
) -> AssetResponse:
    try:
        asset = await _svc(db).update_asset(
            org_id=current_user.org_id, asset_id=asset_id, data=body
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return AssetResponse.model_validate(asset)


@router.delete("/{asset_id}", summary="Delete an asset")
async def delete_asset(asset_id: str, current_user: CurrentUser, db: DBSession) -> Response:
    try:
        await _svc(db).delete_asset(org_id=current_user.org_id, asset_id=asset_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/discover", response_model=dict, summary="Trigger asset discovery (stub)")
async def discover_assets(body: AssetDiscoverRequest, current_user: CurrentUser) -> dict:
    """Stub endpoint — queues a discovery scan for the given CIDR block."""
    return {
        "message": f"Discovery scan queued for {body.cidr}",
        "cidr": body.cidr,
        "status": "queued",
    }
