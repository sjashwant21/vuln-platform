import asyncio
import json
import os

import structlog
from celery import shared_task
from sqlalchemy import select

from app.domain.enums import ScanStatus
from app.infrastructure.database.connection import get_session_factory
from app.infrastructure.database.models import ScanJobModel
from app.infrastructure.database.repositories.asset_repository import SQLAssetRepository
from app.infrastructure.database.repositories.scan_repository import SQLScanRepository

logger = structlog.get_logger(__name__)


def _map_trivy_severity(trivy_severity: str) -> str:
    """Map Trivy severities to our internal severity enum values."""
    mapping = {
        "CRITICAL": "critical",
        "HIGH": "high",
        "MEDIUM": "medium",
        "LOW": "low",
        "UNKNOWN": "info",
    }
    return mapping.get(trivy_severity.upper(), "info")


async def _parse_trivy_report_async(job_id: str, filepath: str) -> None:
    """Async core logic for parsing a Trivy JSON report."""
    factory = get_session_factory()
    async with factory() as session:
        scan_repo = SQLScanRepository(session)
        asset_repo = SQLAssetRepository(session)

        job = (
            await session.execute(select(ScanJobModel).where(ScanJobModel.id == job_id))
        ).scalar_one_or_none()

        if not job:
            logger.error("scan_job_not_found", job_id=job_id)
            return

        org_id = job.organization_id

        await scan_repo.update_job_status(job_id, ScanStatus.RUNNING)
        await session.commit()

        try:
            with open(filepath, encoding="utf-8") as f:
                report_data = json.load(f)

            findings_created = 0
            results = report_data.get("Results", [])

            for result in results:
                target_name = result.get("Target", "unknown-target")

                # Upsert asset for the target (e.g. docker image)
                # Since AssetModel requires an ip_address, we use a placeholder and put the name in hostname
                asset = await asset_repo.upsert_asset(
                    {
                        "organization_id": org_id,
                        "ip_address": "0.0.0.0",
                        "hostname": target_name,
                        "asset_type": "container_image",
                    }
                )
                await session.commit()

                vulnerabilities = result.get("Vulnerabilities", [])
                for vuln in vulnerabilities:
                    cve_id = vuln.get("VulnerabilityID", "")
                    title = vuln.get("Title", cve_id)
                    description = vuln.get("Description", "")
                    severity = _map_trivy_severity(vuln.get("Severity", "UNKNOWN"))

                    cvss_score = None
                    cvss_data = vuln.get("CVSS", {})
                    # Try to extract the highest CVSS v3 score available
                    for _provider, scores in cvss_data.items():
                        if "V3Score" in scores:
                            score = scores["V3Score"]
                            if cvss_score is None or score > cvss_score:
                                cvss_score = score

                    finding_data = {
                        "scan_job_id": job.id,
                        "asset_id": asset.id,
                        "severity": severity,
                        "title": f"{cve_id}: {title}" if cve_id and title != cve_id else title,
                        "description": description or "No description provided.",
                        "cve_ids": [cve_id] if cve_id else [],
                        "cvss_score": cvss_score,
                        "raw_output": vuln,
                    }

                    await scan_repo.create_finding(finding_data)
                    findings_created += 1

            await session.commit()

            # Mark complete
            await scan_repo.update_job_status(
                job_id,
                ScanStatus.COMPLETED,
                extra_data={
                    "result_summary": {
                        "findings_count": findings_created,
                        "trivy_targets": len(results),
                    }
                },
            )
            await session.commit()

        except Exception as e:
            logger.exception("trivy_parse_failed", job_id=job_id, error=str(e))
            await session.rollback()
            await scan_repo.update_job_status(
                job_id, ScanStatus.FAILED, extra_data={"error_message": str(e)}
            )
            await session.commit()
        finally:
            # Clean up the temp file
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as e:
                    logger.warning("failed_to_delete_temp_file", filepath=filepath, error=str(e))


@shared_task(bind=True, name="app.workers.tasks.trivy_scanner.parse_trivy_report_task")
def parse_trivy_report_task(self, job_id: str, filepath: str) -> None:
    """Celery task entrypoint for parsing Trivy reports."""
    asyncio.run(_parse_trivy_report_async(job_id, filepath))

    # Trigger AI Analyst to generate remediation plans for the findings
    from app.workers.tasks.analyst import run_ai_analysis_task

    run_ai_analysis_task.delay(job_id)
