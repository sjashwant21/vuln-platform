"""
Pure domain models for the AI Security Analyst module.

Design principles:
  - Frozen dataclasses: analysis outputs are immutable once produced
  - Every field has a clear business meaning — no "misc" or "extra" dicts
  - Confidence scores are mandatory on every claim — forces the model
    to express uncertainty rather than fabricate certainty
  - All CVE references must come from the input set (enforced by the
    prompt, validated by the parser)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ── Enumerations ───────────────────────────────────────────────

class RiskLevel(str, Enum):
    CRITICAL  = "critical"
    HIGH      = "high"
    MEDIUM    = "medium"
    LOW       = "low"
    INFO      = "info"

    @property
    def priority_order(self) -> int:
        return {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}[self.value]


class RemediationEffort(str, Enum):
    IMMEDIATE  = "immediate"   # Hours — apply now
    SHORT_TERM = "short_term"  # Days — plan this sprint
    MEDIUM_TERM = "medium_term" # Weeks — schedule
    LONG_TERM  = "long_term"   # Months — roadmap item


class AnalysisStage(str, Enum):
    TRIAGE            = "triage"
    TECHNICAL         = "technical"
    RISK_PRIORITY     = "risk_priority"
    REMEDIATION       = "remediation"
    EXECUTIVE         = "executive"


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI    = "openai"
    GEMINI    = "gemini"
    GROQ      = "groq"       # Groq free API — LLaMA 3 70B (recommended)
    LOCAL     = "local"      # Ollama / llama.cpp / vLLM


# ── Input models ───────────────────────────────────────────────

@dataclass(frozen=True)
class VulnerabilityInput:
    """One vulnerability from the scanner, passed into the analyst."""
    cve_id:       str
    title:        str
    severity:     str
    cvss_score:   float | None
    cvss_vector:  str | None
    description:  str
    service:      str
    port:         int | None
    affected_version: str | None
    has_public_exploit: bool
    has_patch:    bool
    references:   tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ServiceInput:
    """One detected service on the target asset."""
    port:    int
    protocol: str
    service: str
    version: str | None
    banner:  str | None = None


@dataclass(frozen=True)
class AnalysisRequest:
    """
    Full input to the AI Security Analyst.
    Constructed by the API layer from scan results.
    """
    asset_id:       str
    asset_hostname: str | None
    asset_ip:       str
    asset_os:       str | None
    asset_criticality: str          # critical | high | medium | low
    internet_exposed:  bool
    services:          tuple[ServiceInput, ...]
    vulnerabilities:   tuple[VulnerabilityInput, ...]
    org_name:          str
    scan_date:         datetime
    additional_context: str = ""   # optional analyst notes


# ── Output models — one per analysis stage ─────────────────────

@dataclass(frozen=True)
class ThreatIndicator:
    """A specific threat signal identified during triage."""
    indicator:   str         # what was observed
    threat_type: str         # e.g. "Remote Code Execution", "Data Exfiltration"
    cve_refs:    tuple[str, ...]  # must be subset of input CVE IDs
    confidence:  float       # 0.0 – 1.0


@dataclass(frozen=True)
class ExecutiveSummary:
    """
    Stage 1 output: 3-paragraph non-technical summary.
    Written for a CTO/CEO audience — no CVE IDs, no CVSS vectors.
    """
    overall_risk_level:  RiskLevel
    headline:            str          # One sentence: the most important finding
    business_impact:     str          # Paragraph: what could go wrong for the business
    key_findings:        tuple[str, ...] # 3-5 bullet points in plain language
    immediate_actions:   tuple[str, ...] # What needs to happen TODAY
    confidence:          float


@dataclass(frozen=True)
class TechnicalFinding:
    """One finding in the technical analysis — maps to a CVE or service issue."""
    cve_id:         str | None      # None for non-CVE findings
    title:          str
    affected_service: str
    affected_port:  int | None
    technical_detail: str           # Deep explanation for security engineers
    attack_scenario: str            # Concrete "attacker does X, then Y, then Z"
    exploitation_complexity: str    # "trivial" | "moderate" | "complex"
    blast_radius:   str             # What an attacker gains
    confidence:     float


@dataclass(frozen=True)
class TechnicalAnalysis:
    """
    Stage 2 output: full technical breakdown for security engineers.
    Each finding must reference a CVE from the input list.
    """
    attack_surface_summary: str
    most_critical_path:     str          # Narrative of the highest-risk attack chain
    findings:               tuple[TechnicalFinding, ...]
    threat_indicators:      tuple[ThreatIndicator, ...]
    lateral_movement_risk:  str
    data_exfiltration_risk: str


@dataclass(frozen=True)
class PrioritizedVuln:
    """One vulnerability after risk prioritization scoring."""
    cve_id:          str
    title:           str
    risk_level:      RiskLevel
    priority_score:  float           # 0.0 – 100.0, composite score
    cvss_score:      float | None
    business_context: str            # Why this is ranked here (not just CVSS)
    exploitability:  str             # "actively exploited" | "poc available" | "theoretical"
    time_to_exploit: str             # Estimated time for skilled attacker
    affected_service: str
    priority_rationale: str          # One sentence explaining the rank


@dataclass(frozen=True)
class RiskPrioritization:
    """
    Stage 3 output: ordered list of vulnerabilities by actual business risk.
    Priority != CVSS score. Context matters.
    """
    prioritized_vulns:    tuple[PrioritizedVuln, ...]
    top_3_rationale:      str    # Why the top 3 are ranked first
    risk_acceptance_note: str    # What it means to accept vs address this risk


@dataclass(frozen=True)
class RemediationStep:
    """One concrete remediation step with enough detail to execute."""
    step_number:   int
    title:         str
    description:   str
    commands:      tuple[str, ...]   # Exact commands where applicable
    verification:  str               # How to confirm the fix worked
    estimated_time: str              # "15 minutes" | "2 hours" | "1 day"
    requires_restart: bool
    requires_downtime: bool


@dataclass(frozen=True)
class RemediationPlan:
    """Remediation plan for one vulnerability."""
    cve_id:         str
    title:          str
    effort:         RemediationEffort
    priority:       int              # 1 = do first
    steps:          tuple[RemediationStep, ...]
    prerequisites:  tuple[str, ...]  # what must be done before this
    rollback_plan:  str
    references:     tuple[str, ...]  # patch links, vendor advisories
    confidence:     float


@dataclass(frozen=True)
class RemediationRecommendations:
    """
    Stage 4 output: actionable remediation for every prioritized finding.
    Steps are concrete enough that a sysadmin can execute them.
    """
    immediate_actions:  tuple[RemediationPlan, ...]   # Do today
    short_term_actions: tuple[RemediationPlan, ...]   # This week
    long_term_actions:  tuple[RemediationPlan, ...]   # This quarter
    quick_wins:         tuple[str, ...]  # Things that take < 30 min with high impact
    estimated_total_effort: str


@dataclass(frozen=True)
class ManagementSummary:
    """
    Stage 5 output: one-page summary for non-technical management.
    No technical jargon. Financial and operational impact framing.
    """
    risk_headline:      str          # "Your infrastructure has 3 critical gaps"
    security_score:     int          # 0-100, simpler than CVSS
    score_label:        str          # "Poor" | "Fair" | "Good" | "Excellent"
    top_risks:          tuple[str, ...]   # Plain language, max 5
    business_risks:     tuple[str, ...]   # Compliance, financial, reputational
    investment_needed:  str          # "2 engineer-days" — for budget conversations
    what_happens_if_ignored: str     # Clear consequence statement
    what_we_recommend:  str          # Single paragraph recommendation


# ── Composite output ───────────────────────────────────────────

@dataclass(frozen=True)
class SecurityAnalysis:
    """
    Complete output of the AI Security Analyst.
    All five stages, plus metadata about the analysis run.
    """
    request:                AnalysisRequest
    executive_summary:      ExecutiveSummary
    technical_analysis:     TechnicalAnalysis
    risk_prioritization:    RiskPrioritization
    remediation_recommendations: RemediationRecommendations
    management_summary:     ManagementSummary

    provider:        LLMProvider
    model_name:      str
    total_tokens:    int
    analysis_time_s: float
    generated_at:    datetime


# ── LLM provider types ─────────────────────────────────────────

@dataclass(frozen=True)
class LLMResponse:
    """Raw response from any LLM provider, normalised to a common format."""
    content:          str
    prompt_tokens:    int
    completion_tokens:int
    model:            str
    finish_reason:    str    # "stop" | "length" | "error"


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for one LLM provider."""
    provider:     LLMProvider
    model:        str
    api_key:      str | None = None
    base_url:     str | None = None   # for local/OpenAI-compatible endpoints
    timeout_s:    int = 120
    temperature:  float = 0.1        # Low = more deterministic
    max_tokens:   int = 4096
    extra_params: dict[str, Any] = field(default_factory=dict)
