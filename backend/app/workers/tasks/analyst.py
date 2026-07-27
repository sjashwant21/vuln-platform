import asyncio
from datetime import UTC, datetime

import structlog
from celery import shared_task
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.application.services.ai_analyst_service import create_analyst_service
from app.config import get_settings
from app.domain.enums import VulnerabilityStatus
from app.domain.models.analysis import (
    AnalysisRequest,
    LLMProvider,
    ProviderConfig,
    ServiceInput,
)
from app.infrastructure.database.connection import get_session_factory
from app.infrastructure.database.models import (
    AssetModel,
    ScanJobModel,
)
from app.infrastructure.database.repositories.vulnerability_repository import (
    SQLVulnerabilityRepository,
)

logger = structlog.get_logger(__name__)


async def _run_ai_analysis_async(job_id: str) -> None:
    """Async core logic for AI analysis."""

    # 1. Fetch scan findings
    factory = get_session_factory()
    async with factory() as session:
        job = (
            await session.execute(
                select(ScanJobModel)
                .options(selectinload(ScanJobModel.findings))
                .where(ScanJobModel.id == job_id)
            )
        ).scalar_one_or_none()

        if not job:
            logger.error("scan_job_not_found_for_analysis", job_id=job_id)
            return

        if not job.findings:
            logger.info("no_findings_to_analyze", job_id=job_id)
            return

        org_id = job.organization_id

        # Group findings by asset_id
        findings_by_asset = {}
        for finding in job.findings:
            findings_by_asset.setdefault(finding.asset_id, []).append(finding)

        cfg = get_settings()
        pc = ProviderConfig(
            provider=LLMProvider.GROQ,
            model=cfg.groq_model,
            api_key=cfg.groq_api_key,
            timeout_s=120,
            temperature=0.1,
            max_tokens=4096,
        )
        ai_svc = create_analyst_service(pc)
        vuln_repo = SQLVulnerabilityRepository(session)

        # Analyze each asset
        for asset_id, findings in findings_by_asset.items():
            asset = (
                await session.execute(
                    select(AssetModel).where(AssetModel.id == asset_id)
                )
            ).scalar_one_or_none()
            if not asset:
                continue

            services = []
            for f in findings:
                if f.port is not None:
                    services.append(
                        ServiceInput(
                            port=f.port,
                            protocol=f.protocol or "tcp",
                            service=f.raw_output.get("service", "unknown"),
                            version=f.raw_output.get("version"),
                            banner=None,
                        )
                    )

            # Create AnalysisRequest
            request = AnalysisRequest(
                asset_id=asset.id,
                asset_hostname=asset.hostname,
                asset_ip=asset.ip_address,
                asset_os=asset.os_fingerprint,
                asset_criticality=asset.criticality,
                internet_exposed=asset.tags.get("internet_exposed", False),
                services=tuple(services),
                vulnerabilities=(),
                org_name="Organization",  # Placeholder since we don't fetch org
                scan_date=job.completed_at or datetime.now(UTC),
                additional_context="",
            )

            try:
                analysis = await ai_svc.analyse(request)
            except Exception as e:
                logger.exception("ai_analysis_failed", job_id=job_id, asset_id=asset_id, error=str(e))
                continue

            # Map TechnicalFindings to VulnerabilityModel
            for finding in analysis.technical_analysis.findings:
                plan_resp = next(
                    (p for p in analysis.remediation_recommendations.short_term_actions if p.cve_id == finding.cve_id),
                    None
                )
                if not plan_resp:
                    plan_resp = next(
                        (p for p in analysis.remediation_recommendations.long_term_actions if p.cve_id == finding.cve_id),
                        None
                    )

                vuln_data = {
                    "organization_id": org_id,
                    "asset_id": asset_id,
                    "title": finding.title,
                    "description": finding.technical_detail,
                    "severity": "medium",
                    "status": VulnerabilityStatus.OPEN.value,
                    "cve_id": finding.cve_id,
                    "port": finding.affected_port,
                    "service": finding.affected_service,
                }

                priority_vuln = next(
                    (v for v in analysis.risk_prioritization.prioritized_vulnerabilities if v.cve_id == finding.cve_id),
                    None
                )
                if priority_vuln:
                    vuln_data["severity"] = priority_vuln.risk_level.value
                    vuln_data["cvss_score"] = priority_vuln.cvss_score
                    vuln_data["risk_score"] = priority_vuln.priority_score

                vuln = await vuln_repo.create(vuln_data)

                if plan_resp:
                    # Generate simple markdown recommendation
                    md_lines = [f"### {plan_resp.title}"]
                    for step in plan_resp.steps:
                        md_lines.append(f"**Step {step.step_number}: {step.title}**")
                        md_lines.append(f"{step.description}")
                        if step.commands:
                            md_lines.append("```bash")
                            md_lines.extend(step.commands)
                            md_lines.append("```")

                    plan_data = {
                        "organization_id": org_id,
                        "vulnerability_id": vuln.id,
                        "ai_model": analysis.model_name,
                        "recommendation_markdown": "\n".join(md_lines),
                        "structured_steps": {
                            "effort": plan_resp.effort.value,
                            "priority": plan_resp.priority,
                            "steps": [
                                {
                                    "step_number": s.step_number,
                                    "title": s.title,
                                    "description": s.description,
                                    "commands": list(s.commands),
                                }
                                for s in plan_resp.steps
                            ],
                            "prerequisites": list(plan_resp.prerequisites),
                            "references": list(plan_resp.references),
                        },
                    }
                    await vuln_repo.create_remediation_plan(plan_data)

            # Save summaries to ScanJobModel
            job.result_summary = {
                **(job.result_summary or {}),
                "executive_summary": jsonable_encoder(analysis.executive_summary),
                "management_summary": jsonable_encoder(analysis.management_summary),
            }
            await session.commit()


@shared_task(bind=True, name="app.workers.tasks.analyst.run_ai_analysis_task")
def run_ai_analysis_task(self, job_id: str) -> None:
    """Celery task for running the AI Analyst on scan findings."""
    asyncio.run(_run_ai_analysis_async(job_id))
