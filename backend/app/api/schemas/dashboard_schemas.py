"""Pydantic v2 schemas for dashboard endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.api.schemas.scan_schemas import ScanJobResponse


class DashboardSummaryResponse(BaseModel):
    total_assets: int
    total_vulnerabilities: int
    open_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    recent_scans: list[ScanJobResponse]


class TrendPoint(BaseModel):
    date: datetime
    score: float


class HealthScoreResponse(BaseModel):
    score: int
    label: str
    grade: str
    critical: int
    high: int
    medium: int
    low: int
    trend: list[TrendPoint]
