import asyncio
import subprocess
import xml.etree.ElementTree as ET

import structlog
from celery import shared_task

from app.domain.enums import ScanStatus
from app.infrastructure.database.connection import session_factory
from app.infrastructure.database.repositories.asset_repository import SQLAssetRepository
from app.infrastructure.database.repositories.scan_repository import SQLScanRepository

logger = structlog.get_logger(__name__)


async def _run_nmap_scan_async(job_id: str) -> None:
    """Async core logic for nmap scanning."""
    async with session_factory() as session:
        scan_repo = SQLScanRepository(session)
        asset_repo = SQLAssetRepository(session)

        # We need the org_id to fetch the job, but we only have job_id.
        # Actually, get_job_by_id currently requires org_id. We might need a bypass for workers,
        # but let's query the raw model to get org_id first.
        from sqlalchemy import select

        from app.infrastructure.database.models import ScanJobModel

        job = (await session.execute(
            select(ScanJobModel).where(ScanJobModel.id == job_id)
        )).scalar_one_or_none()

        if not job:
            logger.error("scan_job_not_found", job_id=job_id)
            return

        org_id = job.organization_id

        await scan_repo.update_job_status(job_id, ScanStatus.RUNNING)
        await session.commit()

        try:
            target_ips = job.target_ips

            # Upsert assets first
            for ip in target_ips:
                await asset_repo.upsert_asset({
                    "organization_id": org_id,
                    "ip_address": ip,
                    "asset_type": "host",
                })
            await session.commit()

            # Execute nmap via subprocess
            # -oX - : output XML to stdout
            # -sV : probe open ports to determine service/version info
            # -T4 : aggressive timing
            cmd = ["nmap", "-oX", "-", "-sV", "-T4"] + target_ips
            logger.info("running_nmap", cmd=" ".join(cmd))

            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode != 0:
                raise Exception(f"Nmap failed: {process.stderr}")

            # Parse XML
            xml_output = process.stdout
            root = ET.fromstring(xml_output)  # noqa: S314

            findings_created = 0
            for host in root.findall("host"):
                address_elem = host.find("address")
                if address_elem is None:
                    continue
                ip_addr = address_elem.get("addr")

                # Get the asset
                asset = await asset_repo.get_by_ip(ip_addr, org_id)
                if not asset:
                    continue

                ports = host.findall(".//port")
                for port_elem in ports:
                    state_elem = port_elem.find("state")
                    if state_elem is None or state_elem.get("state") != "open":
                        continue

                    port_num = int(port_elem.get("portid"))
                    protocol = port_elem.get("protocol")

                    service_elem = port_elem.find("service")
                    service_name = service_elem.get("name") if service_elem is not None else "unknown"
                    service_version = service_elem.get("version") if service_elem is not None else None

                    # Upsert port
                    await asset_repo.upsert_port(
                        asset.id,
                        {
                            "port": port_num,
                            "protocol": protocol,
                            "service": service_name,
                            "service_version": service_version,
                            "state": "open"
                        }
                    )

                    # Create finding for the open port/service
                    finding_data = {
                        "scan_job_id": job.id,
                        "asset_id": asset.id,
                        "port": port_num,
                        "protocol": protocol,
                        "severity": "info",
                        "title": f"Open Port: {port_num}/{protocol} ({service_name})",
                        "description": f"Service {service_name} {service_version or ''} is running on port {port_num}.",
                        "raw_output": {"service": service_name, "version": service_version}
                    }
                    await scan_repo.create_finding(finding_data)
                    findings_created += 1

            await session.commit()

            # Mark complete
            await scan_repo.update_job_status(
                job_id,
                ScanStatus.COMPLETED,
                extra_data={"result_summary": {"findings_count": findings_created}}
            )
            await session.commit()

        except Exception as e:
            logger.exception("nmap_scan_failed", job_id=job_id, error=str(e))
            await session.rollback()
            await scan_repo.update_job_status(
                job_id,
                ScanStatus.FAILED,
                extra_data={"error_message": str(e)}
            )
            await session.commit()


@shared_task(bind=True, name="app.workers.tasks.scanner.run_nmap_scan_task")
def run_nmap_scan_task(self, job_id: str) -> None:
    """Celery task entrypoint."""
    asyncio.run(_run_nmap_scan_async(job_id))
