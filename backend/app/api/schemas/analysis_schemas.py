"""
Pydantic v2 request/response schemas for the AI analysis API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Request schemas ────────────────────────────────────────────

class VulnerabilityInputSchema(BaseModel):
    cve_id:       str   = Field(..., pattern=r"^CVE-\d{4}-\d{4,}$")
    title:        str   = Field(..., min_length=1, max_length=500)
    severity:     Literal["critical", "high", "medium", "low", "info"] = "medium"
    cvss_score:   float | None = Field(default=None, ge=0.0, le=10.0)
    cvss_vector:  str   | None = None
    description:  str   = Field(..., min_length=1)
    service:      str   = Field(..., min_length=1, max_length=100)
    port:         int   | None = Field(default=None, ge=1, le=65535)
    affected_version:  str | None = None
    has_public_exploit: bool = False
    has_patch:    bool  = False
    references:   list[str] = Field(default_factory=list, max_length=10)

    @field_validator("references", mode="before")
    @classmethod
    def _cap_refs(cls, v: list) -> list:
        return v[:10] if v else []


class ServiceInputSchema(BaseModel):
    port:     int    = Field(..., ge=1, le=65535)
    protocol: str    = Field(default="tcp", max_length=10)
    service:  str    = Field(..., min_length=1, max_length=100)
    version:  str | None = Field(default=None, max_length=100)
    banner:   str | None = Field(default=None, max_length=500)


class AnalyseRequest(BaseModel):
    """Request body for POST /v1/analysis/analyse"""

    asset_id:         str  = Field(..., min_length=1, max_length=36)
    asset_hostname:   str | None = Field(default=None, max_length=255)
    asset_ip:         str  = Field(..., min_length=7, max_length=45)
    asset_os:         str | None = Field(default=None, max_length=255)
    asset_criticality:Literal["critical", "high", "medium", "low"] = "medium"
    internet_exposed: bool = False
    services:         list[ServiceInputSchema] = Field(default_factory=list, max_length=50)
    vulnerabilities:  list[VulnerabilityInputSchema] = Field(..., min_length=1, max_length=100)
    org_name:         str  = Field(..., min_length=1, max_length=255)
    scan_date:        datetime | None = None
    additional_context: str = Field(default="", max_length=500)

    provider: Literal["anthropic", "openai", "gemini", "local"] = "anthropic"
    model:    str | None = Field(default=None, max_length=100)

    @field_validator("vulnerabilities")
    @classmethod
    def _unique_cves(cls, v: list) -> list:
        seen: set[str] = set()
        unique = []
        for vuln in v:
            if vuln.cve_id not in seen:
                seen.add(vuln.cve_id)
                unique.append(vuln)
        return unique


# ── Response schemas ───────────────────────────────────────────

class ExecutiveSummaryResponse(BaseModel):
    overall_risk_level: str
    headline:           str
    business_impact:    str
    key_findings:       list[str]
    immediate_actions:  list[str]
    confidence:         float

    model_config = {"from_attributes": True}


class TechnicalFindingResponse(BaseModel):
    cve_id:                  str | None
    title:                   str
    affected_service:        str
    affected_port:           int | None
    technical_detail:        str
    attack_scenario:         str
    exploitation_complexity: str
    blast_radius:            str
    confidence:              float

    model_config = {"from_attributes": True}


class ThreatIndicatorResponse(BaseModel):
    indicator:   str
    threat_type: str
    cve_refs:    list[str]
    confidence:  float

    model_config = {"from_attributes": True}


class TechnicalAnalysisResponse(BaseModel):
    attack_surface_summary: str
    most_critical_path:     str
    findings:               list[TechnicalFindingResponse]
    threat_indicators:      list[ThreatIndicatorResponse]
    lateral_movement_risk:  str
    data_exfiltration_risk: str

    model_config = {"from_attributes": True}


class PrioritizedVulnResponse(BaseModel):
    cve_id:            str
    title:             str
    risk_level:        str
    priority_score:    float
    cvss_score:        float | None
    business_context:  str
    exploitability:    str
    time_to_exploit:   str
    affected_service:  str
    priority_rationale:str

    model_config = {"from_attributes": True}


class RiskPrioritizationResponse(BaseModel):
    prioritized_vulns:    list[PrioritizedVulnResponse]
    top_3_rationale:      str
    risk_acceptance_note: str

    model_config = {"from_attributes": True}


class RemediationStepResponse(BaseModel):
    step_number:       int
    title:             str
    description:       str
    commands:          list[str]
    verification:      str
    estimated_time:    str
    requires_restart:  bool
    requires_downtime: bool

    model_config = {"from_attributes": True}


class RemediationPlanResponse(BaseModel):
    cve_id:        str
    title:         str
    effort:        str
    priority:      int
    steps:         list[RemediationStepResponse]
    prerequisites: list[str]
    rollback_plan: str
    references:    list[str]
    confidence:    float

    model_config = {"from_attributes": True}


class RemediationRecommendationsResponse(BaseModel):
    immediate_actions:      list[RemediationPlanResponse]
    short_term_actions:     list[RemediationPlanResponse]
    long_term_actions:      list[RemediationPlanResponse]
    quick_wins:             list[str]
    estimated_total_effort: str

    model_config = {"from_attributes": True}


class ManagementSummaryResponse(BaseModel):
    risk_headline:           str
    security_score:          int
    score_label:             str
    top_risks:               list[str]
    business_risks:          list[str]
    investment_needed:       str
    what_happens_if_ignored: str
    what_we_recommend:       str

    model_config = {"from_attributes": True}


class SecurityAnalysisResponse(BaseModel):
    asset_id:                    str
    generated_at:                datetime
    provider:                    str
    model_name:                  str
    total_tokens:                int
    analysis_time_s:             float
    executive_summary:           ExecutiveSummaryResponse
    technical_analysis:          TechnicalAnalysisResponse
    risk_prioritization:         RiskPrioritizationResponse
    remediation_recommendations: RemediationRecommendationsResponse
    management_summary:          ManagementSummaryResponse


# ── Conversion helper ──────────────────────────────────────────

def analysis_to_response(analysis: object) -> SecurityAnalysisResponse:
    """Convert SecurityAnalysis domain object to API response."""
    import dataclasses
    from app.domain.models.analysis import SecurityAnalysis

    a: SecurityAnalysis = analysis  # type: ignore[assignment]

    def _steps(steps: tuple) -> list[RemediationStepResponse]:
        return [
            RemediationStepResponse(
                step_number=      s.step_number,
                title=            s.title,
                description=      s.description,
                commands=         list(s.commands),
                verification=     s.verification,
                estimated_time=   s.estimated_time,
                requires_restart= s.requires_restart,
                requires_downtime=s.requires_downtime,
            )
            for s in steps
        ]

    def _plans(plans: tuple) -> list[RemediationPlanResponse]:
        return [
            RemediationPlanResponse(
                cve_id=       p.cve_id,
                title=        p.title,
                effort=       p.effort.value,
                priority=     p.priority,
                steps=        _steps(p.steps),
                prerequisites=list(p.prerequisites),
                rollback_plan=p.rollback_plan,
                references=   list(p.references),
                confidence=   p.confidence,
            )
            for p in plans
        ]

    es = a.executive_summary
    ta = a.technical_analysis
    rp = a.risk_prioritization
    rr = a.remediation_recommendations
    ms = a.management_summary

    return SecurityAnalysisResponse(
        asset_id=       a.request.asset_id,
        generated_at=   a.generated_at,
        provider=       a.provider.value,
        model_name=     a.model_name,
        total_tokens=   a.total_tokens,
        analysis_time_s=a.analysis_time_s,

        executive_summary=ExecutiveSummaryResponse(
            overall_risk_level=es.overall_risk_level.value,
            headline=          es.headline,
            business_impact=   es.business_impact,
            key_findings=      list(es.key_findings),
            immediate_actions= list(es.immediate_actions),
            confidence=        es.confidence,
        ),

        technical_analysis=TechnicalAnalysisResponse(
            attack_surface_summary=ta.attack_surface_summary,
            most_critical_path=    ta.most_critical_path,
            findings=[
                TechnicalFindingResponse(
                    cve_id=                  f.cve_id,
                    title=                   f.title,
                    affected_service=        f.affected_service,
                    affected_port=           f.affected_port,
                    technical_detail=        f.technical_detail,
                    attack_scenario=         f.attack_scenario,
                    exploitation_complexity= f.exploitation_complexity,
                    blast_radius=            f.blast_radius,
                    confidence=              f.confidence,
                )
                for f in ta.findings
            ],
            threat_indicators=[
                ThreatIndicatorResponse(
                    indicator=  i.indicator,
                    threat_type=i.threat_type,
                    cve_refs=   list(i.cve_refs),
                    confidence= i.confidence,
                )
                for i in ta.threat_indicators
            ],
            lateral_movement_risk= ta.lateral_movement_risk,
            data_exfiltration_risk=ta.data_exfiltration_risk,
        ),

        risk_prioritization=RiskPrioritizationResponse(
            prioritized_vulns=[
                PrioritizedVulnResponse(
                    cve_id=            v.cve_id,
                    title=             v.title,
                    risk_level=        v.risk_level.value,
                    priority_score=    v.priority_score,
                    cvss_score=        v.cvss_score,
                    business_context=  v.business_context,
                    exploitability=    v.exploitability,
                    time_to_exploit=   v.time_to_exploit,
                    affected_service=  v.affected_service,
                    priority_rationale=v.priority_rationale,
                )
                for v in rp.prioritized_vulns
            ],
            top_3_rationale=     rp.top_3_rationale,
            risk_acceptance_note=rp.risk_acceptance_note,
        ),

        remediation_recommendations=RemediationRecommendationsResponse(
            immediate_actions=     _plans(rr.immediate_actions),
            short_term_actions=    _plans(rr.short_term_actions),
            long_term_actions=     _plans(rr.long_term_actions),
            quick_wins=            list(rr.quick_wins),
            estimated_total_effort=rr.estimated_total_effort,
        ),

        management_summary=ManagementSummaryResponse(
            risk_headline=          ms.risk_headline,
            security_score=         ms.security_score,
            score_label=            ms.score_label,
            top_risks=              list(ms.top_risks),
            business_risks=         list(ms.business_risks),
            investment_needed=      ms.investment_needed,
            what_happens_if_ignored=ms.what_happens_if_ignored,
            what_we_recommend=      ms.what_we_recommend,
        ),
    )
