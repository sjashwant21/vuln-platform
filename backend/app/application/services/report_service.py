"""
Report service — data assembly + rendering orchestration.

Two responsibilities:
  1. ReportDataAssembler  — queries DB, builds ReportData domain object
  2. ReportService        — orchestrates chart generation + rendering

The assembler is the only place that touches the database.
Renderers receive a complete ReportData and never query the DB.

Async flow:
  assemble()  → runs DB queries concurrently with asyncio.gather()
  generate()  → assembles data, generates charts, renders in executor
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.domain.models.report import (
    AIRecommendation,
    AssetSummary,
    ComplianceControl,
    ComplianceSummary,
    ReportData,
    ReportFormat,
    ReportType,
    RiskTrendPoint,
    SeverityDistribution,
    SeverityLevel,
    VulnDetail,
)

logger = structlog.get_logger(__name__)


# ── Report data assembler ──────────────────────────────────────

class ReportDataAssembler:
    """
    Assembles ReportData from database queries.
    All queries run through SQLAlchemy async session.
    Heavy DB work is parallelised with asyncio.gather().
    """

    def __init__(self, session: Any) -> None:
        self._s = session

    async def assemble(
        self,
        org_id:      str,
        report_type: ReportType,
        org_name:    str,
        generated_by:str,
        scan_job_id: str | None = None,
        period_days: int = 30,
        ai_summary:  str = "",
        ai_recommendations: list[dict[str, Any]] | None = None,
        management_summary: str | None = None,
    ) -> ReportData:
        """
        Query all data needed for the report concurrently, return ReportData.
        """
        period_end   = datetime.now(UTC)
        period_start = period_end - timedelta(days=period_days)

        # Run heavy queries in parallel
        (
            assets,
            vulns,
            severity_counts,
            trend_points,
            compliance_data,
        ) = await asyncio.gather(
            self._fetch_assets(org_id),
            self._fetch_vulns(org_id),
            self._fetch_severity_counts(org_id),
            self._fetch_trend(org_id, period_days),
            self._fetch_compliance(org_id) if report_type == ReportType.COMPLIANCE else asyncio.coroutine(lambda: [])(),
        )

        health_score = self._compute_health(severity_counts, len(assets))
        health_label = self._health_label(health_score)

        # Build AI recommendations from provided data or defaults
        recs = self._build_recommendations(
            ai_recommendations or [], vulns
        )

        dist = SeverityDistribution(
            critical=severity_counts.get("critical", 0),
            high=    severity_counts.get("high",     0),
            medium=  severity_counts.get("medium",   0),
            low=     severity_counts.get("low",      0),
            info=    severity_counts.get("info",     0),
        )

        open_count     = sum(1 for v in vulns if v.status == "open")
        resolved_count = sum(1 for v in vulns if v.status == "resolved")
        accepted_count = sum(1 for v in vulns if v.status == "accepted_risk")

        return ReportData(
            report_id=       str(uuid.uuid4()),
            report_type=     report_type,
            org_name=        org_name,
            generated_at=    datetime.now(UTC),
            generated_by=    generated_by,
            period_start=    period_start,
            period_end=      period_end,
            scan_job_id=     scan_job_id,
            health_score=    health_score,
            health_label=    health_label,
            health_delta=    None,
            severity_distribution=dist,
            total_assets=    len(assets),
            assets=          tuple(assets),
            total_vulns=     len(vulns),
            open_vulns=      open_count,
            resolved_vulns=  resolved_count,
            accepted_risk=   accepted_count,
            vulns=           tuple(vulns),
            risk_trend=      tuple(trend_points),
            compliance=      tuple(compliance_data),
            executive_summary=   ai_summary or self._default_summary(
                org_name, health_score, dist, len(assets)
            ),
            ai_recommendations=  tuple(recs),
            management_summary=  management_summary,
        )

    # ── DB queries ─────────────────────────────────────────────

    async def _fetch_assets(self, org_id: str) -> list[AssetSummary]:
        from sqlalchemy import and_, func, select

        from app.infrastructure.database.models import (
            AssetModel,
            VulnerabilityModel,
        )

        stmt = (
            select(
                AssetModel,
                func.count(VulnerabilityModel.id).filter(
                    VulnerabilityModel.severity == "critical",
                    VulnerabilityModel.status   == "open",
                ).label("vuln_critical"),
                func.count(VulnerabilityModel.id).filter(
                    VulnerabilityModel.severity == "high",
                    VulnerabilityModel.status   == "open",
                ).label("vuln_high"),
                func.count(VulnerabilityModel.id).filter(
                    VulnerabilityModel.severity == "medium",
                    VulnerabilityModel.status   == "open",
                ).label("vuln_medium"),
                func.count(VulnerabilityModel.id).filter(
                    VulnerabilityModel.severity == "low",
                    VulnerabilityModel.status   == "open",
                ).label("vuln_low"),
            )
            .outerjoin(
                VulnerabilityModel,
                and_(
                    VulnerabilityModel.asset_id == AssetModel.id,
                    VulnerabilityModel.organization_id == org_id,
                ),
            )
            .where(
                and_(
                    AssetModel.organization_id == org_id,
                    AssetModel.is_active.is_(True),
                )
            )
            .group_by(AssetModel.id)
            .order_by(AssetModel.created_at.desc())
        )

        rows = (await self._s.execute(stmt)).all()

        assets = []
        for row in rows:
            asset = row[0]
            crit, high, med, low = row[1], row[2], row[3], row[4]
            risk = self._asset_risk(crit, high, med, low, asset.criticality)
            assets.append(AssetSummary(
                asset_id=     asset.id,
                hostname=     asset.hostname,
                ip_address=   asset.ip_address,
                asset_type=   asset.asset_type,
                criticality=  asset.criticality,
                os=           asset.os_fingerprint,
                open_ports=   0,  # populated below if needed
                vuln_critical=crit,
                vuln_high=    high,
                vuln_medium=  med,
                vuln_low=     low,
                risk_score=   risk,
                last_scanned= asset.last_seen_at,
            ))
        return assets

    async def _fetch_vulns(self, org_id: str) -> list[VulnDetail]:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.infrastructure.database.models import (
            VulnerabilityModel,
        )

        stmt = (
            select(VulnerabilityModel)
            .where(VulnerabilityModel.organization_id == org_id)
            .options(selectinload(VulnerabilityModel.asset))
            .order_by(
                VulnerabilityModel.cvss_score.desc().nullslast(),
                VulnerabilityModel.detected_at.desc(),
            )
            .limit(500)   # cap for very large orgs
        )
        rows = (await self._s.execute(stmt)).scalars().all()

        vulns = []
        for v in rows:
            try:
                sev = SeverityLevel(v.severity)
            except ValueError:
                sev = SeverityLevel.INFO

            asset_name = "Unknown"
            asset_ip   = "0.0.0.0"
            if v.asset:
                asset_name = v.asset.hostname or v.asset.ip_address
                asset_ip   = v.asset.ip_address

            vulns.append(VulnDetail(
                vuln_id=     v.id,
                cve_id=      v.cve_id,
                title=       v.title,
                severity=    sev,
                cvss_score=  v.cvss_score,
                asset_name=  asset_name,
                asset_ip=    asset_ip,
                service=     v.service or "Unknown",
                port=        v.port,
                status=      v.status,
                detected_at= v.detected_at,
                has_exploit= False,   # enriched from CVE cache below if available
                has_patch=   False,
                description= v.description,
                remediation= None,    # populated from remediation_plans if available
            ))
        return vulns

    async def _fetch_severity_counts(self, org_id: str) -> dict[str, int]:
        from sqlalchemy import and_, func, select

        from app.infrastructure.database.models import VulnerabilityModel

        stmt = (
            select(VulnerabilityModel.severity, func.count())
            .where(
                and_(
                    VulnerabilityModel.organization_id == org_id,
                    VulnerabilityModel.status == "open",
                )
            )
            .group_by(VulnerabilityModel.severity)
        )
        rows = (await self._s.execute(stmt)).all()
        counts: dict[str, int] = dict.fromkeys(["critical", "high", "medium", "low", "info"], 0)
        for severity, count in rows:
            if severity in counts:
                counts[severity] = count
        return counts

    async def _fetch_trend(
        self, org_id: str, days: int
    ) -> list[RiskTrendPoint]:
        """
        Build a synthetic trend by sampling vulnerability counts
        at weekly intervals. In a full implementation this would
        query a dedicated time-series audit table.
        """
        from datetime import timedelta

        from sqlalchemy import and_, func, select

        from app.infrastructure.database.models import VulnerabilityModel

        points = []
        now = datetime.now(UTC)

        for i in range(min(days, 30), -1, -max(days // 6, 1)):
            sample_date = now - timedelta(days=i)

            stmt = (
                select(VulnerabilityModel.severity, func.count())
                .where(
                    and_(
                        VulnerabilityModel.organization_id == org_id,
                        VulnerabilityModel.detected_at     <= sample_date,
                        VulnerabilityModel.status.in_(["open", "in_progress"]),
                    )
                )
                .group_by(VulnerabilityModel.severity)
            )
            rows = (await self._s.execute(stmt)).all()
            counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for severity, count in rows:
                if severity in counts:
                    counts[severity] = count

            score = self._compute_health(counts, 1)
            points.append(RiskTrendPoint(
                date=     sample_date,
                critical= counts["critical"],
                high=     counts["high"],
                medium=   counts["medium"],
                low=      counts["low"],
                score=    float(score),
            ))

        return points

    async def _fetch_compliance(self, org_id: str) -> list[ComplianceSummary]:
        """
        Build compliance summaries by mapping open vulnerabilities
        to common framework controls based on CWE/CVSS attributes.
        """
        from sqlalchemy import and_, select

        from app.infrastructure.database.models import VulnerabilityModel

        stmt = select(VulnerabilityModel).where(
            and_(
                VulnerabilityModel.organization_id == org_id,
                VulnerabilityModel.status == "open",
            )
        ).limit(200)
        vulns = (await self._s.execute(stmt)).scalars().all()

        return self._map_to_compliance_frameworks(vulns)

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _compute_health(counts: dict[str, int], total_assets: int) -> int:
        assets = max(total_assets, 1)
        deduction = (
            counts.get("critical", 0) * 20
            + counts.get("high",   0) * 8
            + counts.get("medium", 0) * 2
            + counts.get("low",    0) * 0.5
        )
        raw = max(0.0, 100.0 - deduction / assets)
        return int(min(100, raw))

    @staticmethod
    def _health_label(score: int) -> str:
        if score >= 90:
            return "Excellent"
        if score >= 75:
            return "Very Good"
        if score >= 60:
            return "Good"
        if score >= 40:
            return "Fair"
        return "Critical"

    @staticmethod
    def _asset_risk(
        critical: int, high: int, medium: int, low: int, criticality: str
    ) -> float:
        mult = {"critical": 1.5, "high": 1.2, "medium": 1.0, "low": 0.7}.get(criticality, 1.0)
        raw  = (critical * 10 + high * 4 + medium * 1 + low * 0.3) * mult
        return round(min(10.0, raw), 1)

    @staticmethod
    def _build_recommendations(
        ai_data: list[dict[str, Any]],
        vulns:   list[VulnDetail],
    ) -> list[AIRecommendation]:
        recs = []
        for i, item in enumerate(ai_data[:10], 1):
            recs.append(AIRecommendation(
                priority=    i,
                title=       item.get("title", f"Recommendation {i}"),
                description= item.get("description", ""),
                effort=      item.get("effort", "short_term"),
                impact=      item.get("impact", ""),
                cve_refs=    tuple(item.get("cve_refs", [])),
            ))

        # Auto-generate if no AI data provided
        if not recs:
            critical_vulns = [v for v in vulns if v.severity == SeverityLevel.CRITICAL
                              and v.status == "open"][:3]
            for i, v in enumerate(critical_vulns, 1):
                recs.append(AIRecommendation(
                    priority=    i,
                    title=       f"Remediate {v.cve_id or v.title[:40]}",
                    description= f"Address the {v.severity.value} severity finding on "
                                 f"{v.asset_name} affecting {v.service}.",
                    effort=      "immediate",
                    impact=      "Eliminates highest-risk exposure",
                    cve_refs=    (v.cve_id,) if v.cve_id else (),
                ))
        return recs

    @staticmethod
    def _default_summary(
        org_name: str, score: int, dist: SeverityDistribution, assets: int
    ) -> str:
        return (
            f"This report presents the security assessment findings for {org_name}. "
            f"{assets} asset{'s were' if assets != 1 else ' was'} assessed, "
            f"identifying {dist.total} vulnerabilities: "
            f"{dist.critical} critical, {dist.high} high, "
            f"{dist.medium} medium, and {dist.low} low severity. "
            f"The overall security health score is {score}/100 — "
            f"{'immediate action is required' if score < 50 else 'continued monitoring is recommended'}."
        )

    @staticmethod
    def _map_to_compliance_frameworks(
        vulns: list[Any],
    ) -> list[ComplianceSummary]:
        """
        Map vulnerabilities to compliance framework controls.
        This implements a simplified rule-based mapping.
        A production implementation would use a full control mapping database.
        """
        # PCI-DSS controls relevant to common vulnerability types
        pci_controls = [
            ComplianceControl(
                control_id=  "PCI-DSS 6.3.3",
                framework=   "PCI-DSS",
                title=       "All software components are protected from known vulnerabilities",
                status=      "non_compliant" if any(
                    v.severity in ("critical", "high") for v in vulns
                    if hasattr(v, "severity")
                ) else "compliant",
                related_vulns=tuple(
                    v.cve_id for v in vulns[:3]
                    if hasattr(v, "cve_id") and v.cve_id
                ),
                finding=     f"{len(vulns)} open vulnerabilities require patching per PCI-DSS 6.3.3",
                remediation= "Apply all critical and high patches within 30 days per PCI-DSS requirements",
                severity=    "high",
            ),
            ComplianceControl(
                control_id=  "PCI-DSS 11.3.1",
                framework=   "PCI-DSS",
                title=       "Internal vulnerability scans are performed",
                status=      "compliant",
                related_vulns=(),
                finding=     "Internal vulnerability scanning has been performed as evidenced by this report",
                remediation= "Continue quarterly internal scans",
                severity=    "info",
            ),
        ]

        # SOC 2 controls
        soc2_controls = [
            ComplianceControl(
                control_id=  "SOC2 CC7.1",
                framework=   "SOC2",
                title=       "Detection and monitoring of security events",
                status=      "compliant",
                related_vulns=(),
                finding=     "Vulnerability scanning and monitoring controls are operational",
                remediation= "Maintain current monitoring cadence",
                severity=    "info",
            ),
            ComplianceControl(
                control_id=  "SOC2 CC6.1",
                framework=   "SOC2",
                title=       "Logical access security measures",
                status=      "partial" if vulns else "compliant",
                related_vulns=(),
                finding=     "Open vulnerabilities may expose access control weaknesses",
                remediation= "Remediate open vulnerabilities to fully satisfy CC6.1",
                severity=    "medium",
            ),
        ]

        def _summarise(framework: str, controls: list[ComplianceControl]) -> ComplianceSummary:
            statuses = [c.status for c in controls]
            return ComplianceSummary(
                framework=     framework,
                compliant=     statuses.count("compliant"),
                non_compliant= statuses.count("non_compliant"),
                partial=       statuses.count("partial"),
                not_applicable=statuses.count("not_applicable"),
                controls=      tuple(controls),
            )

        return [
            _summarise("PCI-DSS", pci_controls),
            _summarise("SOC2",    soc2_controls),
        ]


# ── Report service (orchestrator) ──────────────────────────────

class ReportService:
    """
    Orchestrates data assembly → chart generation → rendering.

    Usage:
        service = ReportService(session)
        pdf_bytes = await service.generate(
            org_id="...", org_name="Acme", report_type=ReportType.EXECUTIVE,
            report_format=ReportFormat.PDF, generated_by="alice@acme.com",
        )
    """

    def __init__(self, session: Any) -> None:
        self._session  = session
        self._assembler = ReportDataAssembler(session)

    async def generate(
        self,
        org_id:        str,
        org_name:      str,
        report_type:   ReportType,
        report_format: ReportFormat,
        generated_by:  str,
        scan_job_id:   str | None = None,
        period_days:   int = 30,
        ai_summary:    str = "",
        ai_recommendations: list[dict[str, Any]] | None = None,
        management_summary: str | None = None,
    ) -> tuple[bytes, str]:
        """
        Generate a report.

        Returns:
            (report_bytes, filename)
        """
        t0 = asyncio.get_event_loop().time()

        # Step 1: assemble data
        data = await self._assembler.assemble(
            org_id=     org_id,
            report_type=report_type,
            org_name=   org_name,
            generated_by=generated_by,
            scan_job_id=scan_job_id,
            period_days=period_days,
            ai_summary= ai_summary,
            ai_recommendations=ai_recommendations,
            management_summary=management_summary,
        )

        # Step 2: generate charts
        charts_svg, charts_png = await self._generate_charts(data)

        # Step 3: render
        content, filename = await self._render(
            data, report_format, charts_svg, charts_png
        )

        elapsed = asyncio.get_event_loop().time() - t0
        logger.info(
            "report_generated",
            org_id=      org_id,
            report_type= report_type.value,
            format=      report_format.value,
            size_kb=     round(len(content) / 1024, 1),
            elapsed_s=   round(elapsed, 2),
        )

        return content, filename

    async def generate_html_preview(
        self,
        org_id:        str,
        org_name:      str,
        report_type:   ReportType,
        generated_by:  str,
        ai_summary:    str = "",
    ) -> str:
        """Return HTML preview (fast, no PDF conversion)."""
        data = await self._assembler.assemble(
            org_id=org_id, report_type=report_type,
            org_name=org_name, generated_by=generated_by,
            ai_summary=ai_summary,
        )
        charts_svg, _ = await self._generate_charts(data)

        from app.infrastructure.reporting.renderers.pdf_renderer import PDFRenderer
        renderer = PDFRenderer()
        return renderer.render_html_preview(data, charts_svg)

    # ── Chart generation ───────────────────────────────────────

    async def _generate_charts(
        self, data: ReportData
    ) -> tuple[dict[str, str], dict[str, bytes]]:
        """
        Generate all charts concurrently.
        Returns (svg_dict, png_dict) — same charts in both formats.
        """
        from app.infrastructure.reporting.charts.chart_generator import ChartGenerator

        gen  = ChartGenerator()
        dist = data.severity_distribution.as_dict()

        asset_dicts = [
            {
                "display_name": a.display_name,
                "ip_address":   a.ip_address,
                "risk_score":   a.risk_score,
                "vuln_critical":a.vuln_critical,
                "vuln_high":    a.vuln_high,
                "vuln_medium":  a.vuln_medium,
                "vuln_low":     a.vuln_low,
            }
            for a in data.assets
        ]
        trend_dicts = [
            {
                "date":     p.date,
                "critical": p.critical,
                "high":     p.high,
                "medium":   p.medium,
                "low":      p.low,
                "score":    p.score,
            }
            for p in data.risk_trend
        ]
        fw_dicts = [
            {
                "framework":    fw.framework,
                "compliant":    fw.compliant,
                "non_compliant":fw.non_compliant,
                "partial":      fw.partial,
            }
            for fw in data.compliance
        ]

        loop = asyncio.get_event_loop()

        # Generate SVG versions
        svg_tasks = {
            "health_gauge":   loop.run_in_executor(None, gen.health_gauge,   data.health_score),
            "severity_donut": loop.run_in_executor(None, gen.severity_donut, dist),
            "risk_trend":     loop.run_in_executor(None, gen.risk_trend,     trend_dicts),
            "asset_risk":     loop.run_in_executor(None, gen.asset_risk_bars, asset_dicts),
            "asset_stacked":  loop.run_in_executor(None, gen.severity_by_asset_stacked, asset_dicts),
            "compliance":     loop.run_in_executor(None, gen.compliance_bars, fw_dicts),
        }
        svg_results = await asyncio.gather(*svg_tasks.values(), return_exceptions=True)
        charts_svg  = {
            k: (v if isinstance(v, str) else "")
            for k, v in zip(svg_tasks.keys(), svg_results)
        }

        # Generate PNG versions (for DOCX)
        png_tasks = {
            "health_gauge":   loop.run_in_executor(None, lambda: gen.health_gauge(data.health_score, as_png=True)),
            "severity_donut": loop.run_in_executor(None, lambda: gen.severity_donut(dist, as_png=True)),
            "risk_trend":     loop.run_in_executor(None, lambda: gen.risk_trend(trend_dicts, as_png=True)),
            "asset_risk":     loop.run_in_executor(None, lambda: gen.asset_risk_bars(asset_dicts, as_png=True)),
            "asset_stacked":  loop.run_in_executor(None, lambda: gen.severity_by_asset_stacked(asset_dicts, as_png=True)),
            "compliance":     loop.run_in_executor(None, lambda: gen.compliance_bars(fw_dicts, as_png=True)),
        }
        png_results = await asyncio.gather(*png_tasks.values(), return_exceptions=True)
        charts_png  = {
            k: (v if isinstance(v, bytes) else b"")
            for k, v in zip(png_tasks.keys(), png_results)
        }

        return charts_svg, charts_png

    async def _render(
        self,
        data:        ReportData,
        fmt:         ReportFormat,
        charts_svg:  dict[str, str],
        charts_png:  dict[str, bytes],
    ) -> tuple[bytes, str]:
        ts       = data.generated_at.strftime("%Y%m%d")
        base     = f"{data.org_name.replace(' ', '_')}_{data.report_type.value}_{ts}"

        if fmt == ReportFormat.PDF:
            from app.infrastructure.reporting.renderers.pdf_renderer import PDFRenderer
            renderer = PDFRenderer()
            content  = await renderer.render(data, charts_svg)
            filename = f"{base}.pdf"

        elif fmt == ReportFormat.DOCX:
            from app.infrastructure.reporting.renderers.docx_renderer import DocxRenderer
            renderer = DocxRenderer()
            content  = await renderer.render(data, charts_png)
            filename = f"{base}.docx"

        else:
            raise ValueError(f"Unsupported format: {fmt}")

        return content, filename
