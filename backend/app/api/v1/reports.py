"""
Reports API router — /v1/reports/*

Endpoints:
  POST /v1/reports/generate          Generate + stream report bytes
  GET  /v1/reports/{id}/download     Download a stored report
  GET  /v1/reports                   List reports for org
  GET  /v1/reports/{id}/preview      HTML preview (fast, no PDF)
"""
from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.report_schemas import GenerateReportRequest
from app.dependencies import CurrentUser, get_db_session
from app.domain.models.report import ReportFormat, ReportType

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])

DBSession = Annotated[AsyncSession, Depends(get_db_session)]


async def _get_org_name(session: AsyncSession, org_id: str) -> str:
    from sqlalchemy import select

    from app.infrastructure.database.models import OrganizationModel
    stmt   = select(OrganizationModel.name).where(OrganizationModel.id == org_id)
    result = (await session.execute(stmt)).scalar_one_or_none()
    return result or "Organisation"


# ── POST /reports/generate ─────────────────────────────────────

@router.post(
    "/generate",
    summary="Generate a security report (PDF or DOCX)",
    description="""
Assembles a report from the current state of the vulnerability database
and renders it to the requested format.

Report types:
- **executive** — 3-page summary for leadership, charts + AI recommendations
- **technical** — Full asset inventory, all vulnerabilities, trend analysis
- **vulnerability** — Focused vulnerability listing with remediation detail
- **compliance** — PCI-DSS / SOC2 control mapping

Generation takes 5–30 seconds depending on data volume and format.
The response streams the binary file directly.
    """,
)
async def generate_report(
    body:         GenerateReportRequest,
    current_user: CurrentUser,
    db:           DBSession,
) -> Response:
    from app.application.services.report_service import ReportService

    org_name = await _get_org_name(db, current_user.org_id)

    try:
        report_type   = ReportType(body.report_type)
        report_format = ReportFormat(body.report_format)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    svc = ReportService(db)

    try:
        content, filename = await svc.generate(
            org_id=     current_user.org_id,
            org_name=   org_name,
            report_type=report_type,
            report_format=report_format,
            generated_by=current_user.email,
            scan_job_id=body.scan_job_id,
            period_days=body.period_days,
            ai_summary= body.ai_summary,
            ai_recommendations=body.ai_recommendations,
            management_summary=body.management_summary,
        )
    except Exception as exc:
        logger.error(
            "report_generation_failed",
            org_id=current_user.org_id,
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {exc}",
        )

    content_types = {
        ReportFormat.PDF:  "application/pdf",
        ReportFormat.DOCX: "application/vnd.openxmlformats-officedocument"
                           ".wordprocessingml.document",
    }

    logger.info(
        "report_served",
        org_id=  current_user.org_id,
        type=    body.report_type,
        format=  body.report_format,
        size_kb= round(len(content) / 1024, 1),
        filename=filename,
    )

    return Response(
        content=content,
        media_type=content_types[report_format],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Filename":   filename,
            "X-Report-Size":       str(len(content)),
        },
    )


# ── GET /reports/preview ───────────────────────────────────────

@router.get(
    "/preview",
    response_class=HTMLResponse,
    summary="HTML preview of a report (fast, no PDF conversion)",
)
async def preview_report(
    current_user: CurrentUser,
    db:           DBSession,
    report_type:  str = Query(default="executive"),
    ai_summary:   str = Query(default=""),
) -> HTMLResponse:
    from app.application.services.report_service import ReportService

    try:
        rt = ReportType(report_type)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid report_type: {report_type}")

    org_name = await _get_org_name(db, current_user.org_id)
    svc      = ReportService(db)

    html = await svc.generate_html_preview(
        org_id=     current_user.org_id,
        org_name=   org_name,
        report_type=rt,
        generated_by=current_user.email,
        ai_summary= ai_summary,
    )
    return HTMLResponse(content=html)
