"""Dashboard service layer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AssetModel,
    ScanJobModel,
    VulnerabilityModel,
)


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_summary(self, org_id: str) -> dict:
        """Return aggregate counts + recent scans for the dashboard."""
        # Total assets
        total_assets_result = await self._s.execute(
            select(func.count()).where(
                and_(AssetModel.organization_id == org_id, AssetModel.is_active.is_(True))
            )
        )
        total_assets = total_assets_result.scalar() or 0

        # Vulnerability counts by severity (open only)
        sev_result = await self._s.execute(
            select(VulnerabilityModel.severity, func.count())
            .where(
                and_(
                    VulnerabilityModel.organization_id == org_id,
                    VulnerabilityModel.status == "open",
                )
            )
            .group_by(VulnerabilityModel.severity)
        )
        sev_counts: dict[str, int] = dict(sev_result.all())

        # Total vulnerabilities (all statuses)
        total_vulns_result = await self._s.execute(
            select(func.count()).where(VulnerabilityModel.organization_id == org_id)
        )
        total_vulnerabilities = total_vulns_result.scalar() or 0

        open_vulns_result = await self._s.execute(
            select(func.count()).where(
                and_(
                    VulnerabilityModel.organization_id == org_id,
                    VulnerabilityModel.status == "open",
                )
            )
        )
        open_vulnerabilities = open_vulns_result.scalar() or 0

        # Recent scans
        scans_result = await self._s.execute(
            select(ScanJobModel)
            .where(ScanJobModel.organization_id == org_id)
            .order_by(ScanJobModel.created_at.desc())
            .limit(5)
        )
        recent_scans = list(scans_result.scalars().all())

        return {
            "total_assets": total_assets,
            "total_vulnerabilities": total_vulnerabilities,
            "open_vulnerabilities": open_vulnerabilities,
            "critical_count": sev_counts.get("critical", 0),
            "high_count": sev_counts.get("high", 0),
            "medium_count": sev_counts.get("medium", 0),
            "low_count": sev_counts.get("low", 0),
            "recent_scans": recent_scans,
        }

    async def get_health_score(self, org_id: str) -> dict:
        """Compute a 0–100 security health score with 7-day trend."""
        sev_result = await self._s.execute(
            select(VulnerabilityModel.severity, func.count())
            .where(
                and_(
                    VulnerabilityModel.organization_id == org_id,
                    VulnerabilityModel.status == "open",
                )
            )
            .group_by(VulnerabilityModel.severity)
        )
        counts: dict[str, int] = dict(sev_result.all())
        critical = counts.get("critical", 0)
        high = counts.get("high", 0)
        medium = counts.get("medium", 0)
        low = counts.get("low", 0)

        assets_result = await self._s.execute(
            select(func.count()).where(
                and_(AssetModel.organization_id == org_id, AssetModel.is_active.is_(True))
            )
        )
        total_assets = max(assets_result.scalar() or 1, 1)

        score = self._compute_score(critical, high, medium, low, total_assets)

        # Build 7-day trend (snapshot score at each day boundary)
        now = datetime.now(UTC)
        trend = []
        for day_offset in range(6, -1, -1):
            sample_date = now - timedelta(days=day_offset)
            sr = await self._s.execute(
                select(VulnerabilityModel.severity, func.count())
                .where(
                    and_(
                        VulnerabilityModel.organization_id == org_id,
                        VulnerabilityModel.detected_at <= sample_date,
                        VulnerabilityModel.status.in_(["open", "in_progress"]),
                    )
                )
                .group_by(VulnerabilityModel.severity)
            )
            day_counts: dict[str, int] = dict(sr.all())
            day_score = self._compute_score(
                day_counts.get("critical", 0),
                day_counts.get("high", 0),
                day_counts.get("medium", 0),
                day_counts.get("low", 0),
                total_assets,
            )
            trend.append({"date": sample_date, "score": float(day_score)})

        label, grade = self._label_grade(score)
        return {
            "score": score,
            "label": label,
            "grade": grade,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "trend": trend,
        }

    @staticmethod
    def _compute_score(critical: int, high: int, medium: int, low: int, total_assets: int) -> int:
        deduction = critical * 20 + high * 8 + medium * 2 + low * 0.5
        raw = max(0.0, 100.0 - deduction / total_assets)
        return int(min(100, raw))

    @staticmethod
    def _label_grade(score: int) -> tuple[str, str]:
        if score >= 90:
            return "Excellent", "A"
        if score >= 75:
            return "Very Good", "B"
        if score >= 60:
            return "Good", "C"
        if score >= 40:
            return "Fair", "D"
        return "Critical", "F"
