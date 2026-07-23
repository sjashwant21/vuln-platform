"""
Risk scoring engine — converts raw CVSS scores into business risk scores.

CVSS is a measure of intrinsic vulnerability severity.
Risk = Severity × Likelihood × Business Impact.

This service adds the Likelihood and Business Impact dimensions
that CVSS deliberately omits.

Scoring model:
  risk_score = cvss_base
             × criticality_multiplier    (0.7 – 1.5)
             × exposure_multiplier       (1.0 – 1.4)
             × exploitability_multiplier (1.0 – 1.5)
             × confidence                (0.3 – 1.0)
             ÷ normalization_factor
  → capped at 10.0, rounded to 2dp

The normalization_factor ensures the maximum theoretical score stays at 10.0
even when all multipliers are at their maximum.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.models.cve import (
    CVE,
    CorrelationMatch,
    CVSSMetrics,
    IntelligenceReport,
    RiskContext,
    Severity,
)


@dataclass(frozen=True)
class ScoredCVE:
    """A CVE with all scoring factors broken down for transparency."""
    cve_id:                str
    cvss_base_score:       float | None
    severity:              Severity
    risk_score:            float
    criticality_factor:    float
    exposure_factor:       float
    exploitability_factor: float
    confidence:            float
    has_public_exploit:    bool
    is_network_exploitable:bool
    patch_available:       bool


@dataclass(frozen=True)
class OrganizationRiskSummary:
    """
    Aggregate risk summary across all assets in an organisation.
    Used for the dashboard health score.
    """
    health_score:       int       # 0-100, higher is better
    letter_grade:       str       # A B C D F
    risk_label:         str       # Healthy / At Risk / Critical
    total_open_vulns:   int
    critical_count:     int
    high_count:         int
    medium_count:       int
    low_count:          int
    max_risk_score:     float
    weighted_risk:      float     # normalised across assets


class RiskScoringService:
    """
    Standalone risk scoring service.
    Can be used independently of the correlation service for
    re-scoring existing vulnerability records when context changes.
    """

    # Maximum possible raw score (all multipliers maxed) for normalisation
    _MAX_RAW = 10.0 * 1.5 * 1.4 * 1.5   # = 31.5
    _NORM    = _MAX_RAW / 10.0            # = 3.15

    def score_cve(
        self,
        cve:        CVE,
        context:    RiskContext,
        confidence: float = 1.0,
    ) -> ScoredCVE:
        """
        Compute a risk score for a single CVE in a given asset context.
        """
        cvss_base = cve.base_score

        # Use 5.0 (medium) as default when CVSS is absent
        base = cvss_base if cvss_base is not None else 5.0

        criticality_factor    = context.asset_criticality.multiplier
        exposure_factor       = self._exposure(context, cve.cvss_v3)
        exploitability_factor = self._exploitability(cve)

        raw = base * criticality_factor * exposure_factor * exploitability_factor * confidence
        risk_score = round(min(10.0, raw / self._NORM * 10.0), 2)

        return ScoredCVE(
            cve_id=                cve.cve_id,
            cvss_base_score=       cvss_base,
            severity=              cve.severity,
            risk_score=            risk_score,
            criticality_factor=    criticality_factor,
            exposure_factor=       exposure_factor,
            exploitability_factor= exploitability_factor,
            confidence=            confidence,
            has_public_exploit=    cve.has_public_exploit,
            is_network_exploitable=bool(cve.cvss_v3 and cve.cvss_v3.is_network_exploitable),
            patch_available=       cve.has_patch,
        )

    def score_report(
        self,
        report:  IntelligenceReport,
        context: RiskContext,
    ) -> IntelligenceReport:
        """
        Re-score all matches in an IntelligenceReport with the given context.
        Returns a new report with updated risk scores.
        """
        rescored = []
        for match in report.matches:
            scored = self.score_cve(match.cve, context, match.confidence)
            rescored.append(
                CorrelationMatch(
                    cve=             match.cve,
                    match_method=    match.match_method,
                    matched_version= match.matched_version,
                    matched_service= match.matched_service,
                    confidence=      match.confidence,
                    risk_score=      scored.risk_score,
                )
            )

        rescored.sort(key=lambda m: m.risk_score, reverse=True)

        return IntelligenceReport(
            service=       report.service,
            version=       report.version,
            query_time_ms= report.query_time_ms,
            matches=       tuple(rescored),
        )

    def compute_org_health(
        self,
        severity_counts: dict[str, int],
        total_assets:    int,
    ) -> OrganizationRiskSummary:
        """
        Compute a 0-100 health score for an organisation.

        Formula:
          deduction = critical*20 + high*8 + medium*2 + low*0.5
          per_asset  = deduction / max(assets, 1)
          score      = max(0, 100 - per_asset), capped at 100

        Letters: A=90+, B=80+, C=70+, D=60+, F=below 60
        """
        critical = severity_counts.get("critical", 0)
        high     = severity_counts.get("high",     0)
        medium   = severity_counts.get("medium",   0)
        low      = severity_counts.get("low",      0)
        total    = critical + high + medium + low

        assets = max(total_assets, 1)
        deduction = (critical * 20 + high * 8 + medium * 2 + low * 0.5)
        per_asset = deduction / assets
        raw_score = max(0.0, min(100.0, 100.0 - per_asset))
        score     = int(raw_score)

        if score >= 90:
            grade, label = "A", "Healthy"
        elif score >= 80:
            grade, label = "B", "Good"
        elif score >= 70:
            grade, label = "C", "Fair"
        elif score >= 60:
            grade, label = "D", "At Risk"
        else:
            grade, label = "F", "Critical"

        max_risk = 10.0 if critical > 0 else (8.0 if high > 0 else (5.0 if medium > 0 else 2.0))
        weighted = round(deduction / assets / 10.0, 2) if assets else 0.0

        return OrganizationRiskSummary(
            health_score=     score,
            letter_grade=     grade,
            risk_label=       label,
            total_open_vulns= total,
            critical_count=   critical,
            high_count=       high,
            medium_count=     medium,
            low_count=        low,
            max_risk_score=   max_risk,
            weighted_risk=    weighted,
        )

    # ── Scoring factor helpers ─────────────────────────────────

    @staticmethod
    def _exposure(ctx: RiskContext, cvss_v3: CVSSMetrics | None) -> float:
        """
        Exposure factor based on asset exposure and CVSSv3 attack vector.
        """
        factor = 1.0

        if ctx.internet_exposed:
            factor += 0.3
            # Network-exploitable CVE + internet-exposed = max exposure risk
            if cvss_v3 and cvss_v3.is_network_exploitable:
                factor += 0.1

        if ctx.data_sensitivity in ("confidential", "secret"):
            factor += 0.05

        return min(1.4, factor)

    @staticmethod
    def _exploitability(cve: CVE) -> float:
        """
        Exploitability factor based on known exploits and CVSS attack properties.
        """
        factor = 1.0

        if cve.has_public_exploit:
            factor += 0.4

        if cve.cvss_v3:
            m = cve.cvss_v3
            if m.is_network_exploitable:
                factor += 0.05
            if m.requires_no_privileges:
                factor += 0.05
            if m.requires_no_interaction:
                factor += 0.05

        return min(1.5, factor)
