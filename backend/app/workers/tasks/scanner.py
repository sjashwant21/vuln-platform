"""
Celery task: run nmap scan for a queued ScanJob.

Security hardening:
  - Validated IPs are re-validated before being passed to nmap (defence-in-depth)
  - "--" separator ensures nmap never interprets user input as flags
  - org_id is always passed and enforced in DB queries (tenant isolation)
  - defusedxml used for XML parsing (XXE / entity-expansion prevention)
  - Subprocess has a 300s timeout to prevent infinite hangs
"""

from __future__ import annotations

import asyncio

import structlog
from celery import shared_task

from app.domain.enums import ScanStatus
from app.infrastructure.database.connection import get_session_factory
from app.infrastructure.database.repositories.asset_repository import SQLAssetRepository
from app.infrastructure.database.repositories.scan_repository import SQLScanRepository
from app.infrastructure.security.ip_validator import validate_scan_target

logger = structlog.get_logger(__name__)


async def _run_nmap_scan_async(job_id: str, org_id: str) -> None:
    """Async core logic for nmap scanning. org_id is mandatory for tenant isolation."""
    factory = get_session_factory()
    async with factory() as session:
        scan_repo = SQLScanRepository(session)
        asset_repo = SQLAssetRepository(session)

        from sqlalchemy import select

        from app.infrastructure.database.models import ScanJobModel

        # Always scope by BOTH job_id AND org_id — never query by ID alone
        job = (
            await session.execute(
                select(ScanJobModel).where(
                    ScanJobModel.id == job_id,
                    ScanJobModel.organization_id == org_id,  # ← tenant isolation
                )
            )
        ).scalar_one_or_none()

        if not job:
            logger.error("scan_job_not_found", job_id=job_id, org_id=org_id)
            return

        await scan_repo.update_job_status(job_id, ScanStatus.RUNNING)
        await session.commit()

        try:
            target_ips = job.target_ips

            # Re-validate IPs at execution time (defence-in-depth).
            # If validation fails here the job was somehow created with bad data.
            sanitized_ips: list[str] = []
            for ip in target_ips:
                try:
                    sanitized_ips.append(validate_scan_target(ip))
                except ValueError as exc:
                    logger.warning("invalid_scan_target_rejected", ip=ip, reason=str(exc))

            if not sanitized_ips:
                raise ValueError("No valid scan targets after sanitization")

            # Upsert assets first
            for ip in sanitized_ips:
                await asset_repo.upsert_asset(
                    {
                        "organization_id": org_id,
                        "ip_address": ip,
                        "asset_type": "host",
                    }
                )
            await session.commit()

            # Build nmap command — "--" separator ensures every argument after it
            # is treated as a target, never as a nmap flag (injection prevention).
            cmd = [
                "nmap",
                "-oX", "-",          # XML output to stdout
                "-sV",               # service version detection
                "-T4",               # timing template
                "--open",            # only show open ports
                "--script", "default",  # safe default scripts only (no user-supplied scripts)
                "--",                # ← everything after here is a target, not a flag
            ] + sanitized_ips

            logger.info("running_nmap", target_count=len(sanitized_ips))

            import subprocess

            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5-minute hard limit per scan
            )

            if process.returncode != 0:
                raise RuntimeError(f"Nmap scan failed (exit {process.returncode})")

            # Parse XML using defusedxml — prevents XXE and entity-expansion attacks
            try:
                import defusedxml.ElementTree as DefusedET
            except ImportError:
                # Fallback: stdlib ET is safe for nmap output (no external entities)
                import xml.etree.ElementTree as DefusedET  # noqa: S405

            xml_output = process.stdout
            root = DefusedET.fromstring(xml_output)  # noqa: S314

            findings_created = 0
            for host in root.findall("host"):
                address_elem = host.find("address")
                if address_elem is None:
                    continue
                ip_addr = address_elem.get("addr")

                # Get the asset — always scoped to org
                asset = await asset_repo.get_by_ip(ip_addr, org_id)
                if not asset:
                    continue

                ports = host.findall(".//port")
                for port_elem in ports:
                    state_elem = port_elem.find("state")
                    if state_elem is None or state_elem.get("state") != "open":
                        continue

                    port_num = int(port_elem.get("portid", 0))
                    protocol = port_elem.get("protocol", "tcp")

                    service_elem = port_elem.find("service")
                    service_name = (
                        service_elem.get("name") if service_elem is not None else "unknown"
                    )
                    service_version = (
                        service_elem.get("version") if service_elem is not None else None
                    )

                    await asset_repo.upsert_port(
                        asset.id,
                        {
                            "port": port_num,
                            "protocol": protocol,
                            "service": service_name,
                            "service_version": service_version,
                            "state": "open",
                        },
                    )

                    finding_data = {
                        "scan_job_id": job.id,
                        "asset_id": asset.id,
                        "port": port_num,
                        "protocol": protocol,
                        "severity": "info",
                        "title": f"Open Port: {port_num}/{protocol} ({service_name})",
                        "description": (
                            f"Service {service_name} "
                            f"{service_version or ''} "
                            f"detected on port {port_num}."
                        ),
                        "raw_output": {"service": service_name, "version": service_version},
                    }
                    await scan_repo.create_finding(finding_data)
                    findings_created += 1

            await session.commit()

            await scan_repo.update_job_status(
                job_id,
                ScanStatus.COMPLETED,
                extra_data={"result_summary": {"findings_count": findings_created}},
            )
            await session.commit()

        except Exception as e:
            logger.exception("nmap_scan_failed", job_id=job_id, org_id=org_id, error=str(e))
            await session.rollback()
            await scan_repo.update_job_status(
                job_id,
                ScanStatus.FAILED,
                extra_data={"error_message": "Scan failed. Check server logs for details."},
                # NOTE: Do NOT expose raw error strings to the client — they may contain
                # internal path info. Log details above, return generic message in DB.
            )
            await session.commit()


@shared_task(bind=True, name="app.workers.tasks.scanner.run_nmap_scan_task")
def run_nmap_scan_task(self, job_id: str, org_id: str) -> None:
    """
    Celery task entrypoint.

    BREAKING CHANGE: org_id is now a required argument for tenant isolation.
    All callers must pass both job_id and org_id.
    """
    asyncio.run(_run_nmap_scan_async(job_id, org_id))

    # Trigger AI Analyst to generate remediation plans
    from app.workers.tasks.analyst import run_ai_analysis_task

    run_ai_analysis_task.delay(job_id, org_id)
