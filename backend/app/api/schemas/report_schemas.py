"""Pydantic v2 schemas for the reporting API."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GenerateReportRequest(BaseModel):
    report_type:   Literal["executive", "technical", "vulnerability", "compliance"]
    report_format: Literal["pdf", "docx"] = "pdf"
    scan_job_id:   str | None = None
    period_days:   int = Field(default=30, ge=7, le=365)
    ai_summary:    str = Field(default="", max_length=2000)
    ai_recommendations: list[dict] = Field(default_factory=list, max_length=10)
    management_summary: str | None = Field(default=None, max_length=3000)


class ReportMetadataResponse(BaseModel):
    report_id:     str
    report_type:   str
    report_format: str
    org_name:      str
    generated_at:  datetime
    generated_by:  str
    health_score:  int
    total_assets:  int
    total_vulns:   int
    open_vulns:    int
    period_start:  datetime
    period_end:    datetime
    filename:      str
    size_bytes:    int
