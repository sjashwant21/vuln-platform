"""Pydantic v2 schemas for asset endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ── Requests ───────────────────────────────────────────────────


class AssetCreateRequest(BaseModel):
    hostname: str | None = Field(default=None, max_length=255)
    ip_address: str = Field(..., max_length=45)
    asset_type: str = Field(default="unknown", max_length=50)
    os_fingerprint: str | None = Field(default=None, max_length=255)
    criticality: str = Field(default="medium", max_length=20)
    tags: dict[str, str] = Field(default_factory=dict)
    is_active: bool = Field(default=True)


class AssetUpdateRequest(BaseModel):
    hostname: str | None = Field(default=None, max_length=255)
    ip_address: str | None = Field(default=None, max_length=45)
    asset_type: str | None = Field(default=None, max_length=50)
    os_fingerprint: str | None = Field(default=None, max_length=255)
    criticality: str | None = Field(default=None, max_length=20)
    tags: dict[str, str] | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class AssetDiscoverRequest(BaseModel):
    cidr: str = Field(..., description="CIDR block to scan for assets, e.g., '192.168.1.0/24'")


# ── Responses ──────────────────────────────────────────────────


class AssetPortResponse(BaseModel):
    id: str
    port: int
    protocol: str
    service: str | None
    service_version: str | None
    state: str
    scanned_at: datetime

    model_config = {"from_attributes": True}


class AssetResponse(BaseModel):
    id: str
    organization_id: str
    hostname: str | None
    ip_address: str
    asset_type: str
    os_fingerprint: str | None
    criticality: str
    tags: dict[str, Any]
    is_active: bool
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime

    ports: list[AssetPortResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    total: int
    limit: int
    offset: int
