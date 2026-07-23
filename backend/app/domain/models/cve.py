"""
Pure domain models for the vulnerability intelligence engine.

These classes carry no ORM, no HTTP, no serialization logic.
They represent the business concepts: what is a CVE, what is a
correlation result, what is a risk-scored finding.

Immutability via frozen dataclasses enforces that domain objects
cannot be accidentally mutated as they flow through the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# ── Severity ───────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "critical"   # CVSS 9.0 – 10.0
    HIGH     = "high"       # CVSS 7.0 – 8.9
    MEDIUM   = "medium"     # CVSS 4.0 – 6.9
    LOW      = "low"        # CVSS 0.1 – 3.9
    NONE     = "none"       # CVSS 0.0
    UNKNOWN  = "unknown"    # No CVSS available

    @classmethod
    def from_cvss(cls, score: float | None) -> Severity:
        if score is None:
            return cls.UNKNOWN
        if score >= 9.0:
            return cls.CRITICAL
        if score >= 7.0:
            return cls.HIGH
        if score >= 4.0:
            return cls.MEDIUM
        if score > 0.0:
            return cls.LOW
        return cls.NONE

    @property
    def display_order(self) -> int:
        """Lower = shown first in sorted lists."""
        return {
            Severity.CRITICAL: 0,
            Severity.HIGH:     1,
            Severity.MEDIUM:   2,
            Severity.LOW:      3,
            Severity.NONE:     4,
            Severity.UNKNOWN:  5,
        }[self]


# ── CVE reference ──────────────────────────────────────────────

@dataclass(frozen=True)
class CVEReference:
    url:  str
    tags: tuple[str, ...] = field(default_factory=tuple)

    def is_patch(self) -> bool:
        return any(t.lower() in ("patch", "vendor advisory") for t in self.tags)

    def is_exploit(self) -> bool:
        return any(t.lower() in ("exploit", "third party advisory") for t in self.tags)


# ── CVSS metrics ───────────────────────────────────────────────

@dataclass(frozen=True)
class CVSSMetrics:
    version:          str           # "3.1" | "3.0" | "2.0"
    base_score:       float
    vector_string:    str
    attack_vector:    str | None = None
    attack_complexity:str | None = None
    privileges_required: str | None = None
    user_interaction: str | None = None
    scope:            str | None = None
    confidentiality:  str | None = None
    integrity:        str | None = None
    availability:     str | None = None

    @property
    def severity(self) -> Severity:
        return Severity.from_cvss(self.base_score)

    @property
    def is_network_exploitable(self) -> bool:
        return self.attack_vector in ("NETWORK", "N")

    @property
    def requires_no_privileges(self) -> bool:
        return self.privileges_required in ("NONE", "N")

    @property
    def requires_no_interaction(self) -> bool:
        return self.user_interaction in ("NONE", "N")

    @property
    def exploitability_score(self) -> float:
        """
        Simple exploitability heuristic (0.0 – 1.0).
        Network-reachable + no privileges + no interaction = worst case.
        """
        score = 0.0
        if self.is_network_exploitable:
            score += 0.5
        if self.requires_no_privileges:
            score += 0.3
        if self.requires_no_interaction:
            score += 0.2
        return round(score, 2)


# ── Core CVE domain model ──────────────────────────────────────

@dataclass(frozen=True)
class CVE:
    """
    Canonical representation of a CVE entry in our system.

    Normalised from NVD API v2 response — all optional fields handled.
    This is what the correlation engine works with; it never sees raw API JSON.
    """
    cve_id:       str
    description:  str
    published_at: datetime | None
    modified_at:  datetime | None
    cvss_v3:      CVSSMetrics | None
    cvss_v2:      CVSSMetrics | None
    cwe_ids:      tuple[str, ...]
    references:   tuple[CVEReference, ...]
    cpe_matches:  tuple[str, ...]   # raw CPE 2.3 strings from NVD

    # ── Derived convenience properties ────────────────────────

    @property
    def primary_cvss(self) -> CVSSMetrics | None:
        """Prefer CVSSv3 over CVSSv2."""
        return self.cvss_v3 or self.cvss_v2

    @property
    def base_score(self) -> float | None:
        m = self.primary_cvss
        return m.base_score if m else None

    @property
    def severity(self) -> Severity:
        return Severity.from_cvss(self.base_score)

    @property
    def has_public_exploit(self) -> bool:
        return any(ref.is_exploit() for ref in self.references)

    @property
    def has_patch(self) -> bool:
        return any(ref.is_patch() for ref in self.references)

    @property
    def year(self) -> int | None:
        try:
            return int(self.cve_id.split("-")[1])
        except (IndexError, ValueError):
            return None


# ── Correlation result ─────────────────────────────────────────

class MatchMethod(str, Enum):
    CPE_EXACT     = "cpe_exact"       # Matched via CPE 2.3 string
    KEYWORD       = "keyword"         # Matched via NVD keyword search
    VERSION_RANGE = "version_range"   # Matched via version range parsing
    CACHE_HIT     = "cache_hit"       # Returned from local DB cache


@dataclass(frozen=True)
class CorrelationMatch:
    """
    A single CVE matched to an input service/version pair.
    Includes the match method for transparency and confidence scoring.
    """
    cve:          CVE
    match_method: MatchMethod
    matched_version: str       # The version string we matched against
    matched_service: str       # The service name we matched against

    # Confidence 0.0 – 1.0: how certain we are this match is real
    confidence:   float = 1.0

    # Risk score 0.0 – 10.0: CVSS × asset × exploitability factors
    risk_score:   float = 0.0

    @property
    def cve_id(self) -> str:
        return self.cve.cve_id

    @property
    def severity(self) -> Severity:
        return self.cve.severity


# ── Risk scoring inputs ────────────────────────────────────────

class AssetCriticality(str, Enum):
    CRITICAL = "critical"   # multiplier 1.5
    HIGH     = "high"       # multiplier 1.2
    MEDIUM   = "medium"     # multiplier 1.0
    LOW      = "low"        # multiplier 0.7

    @property
    def multiplier(self) -> float:
        return {
            AssetCriticality.CRITICAL: 1.5,
            AssetCriticality.HIGH:     1.2,
            AssetCriticality.MEDIUM:   1.0,
            AssetCriticality.LOW:      0.7,
        }[self]


@dataclass(frozen=True)
class RiskContext:
    """
    Caller-provided context that adjusts the raw CVSS score
    into a business-relevant risk score.
    """
    asset_criticality:  AssetCriticality = AssetCriticality.MEDIUM
    internet_exposed:   bool = False
    has_active_session: bool = False   # e.g. users actively logged in
    data_sensitivity:   str = "internal"  # public | internal | confidential | secret


# ── Intelligence report ────────────────────────────────────────

@dataclass(frozen=True)
class IntelligenceReport:
    """
    Final output of the vulnerability intelligence engine
    for one (service, version) query.
    """
    service:      str
    version:      str
    query_time_ms: float
    matches:      tuple[CorrelationMatch, ...]

    @property
    def total_findings(self) -> int:
        return len(self.matches)

    @property
    def critical_count(self) -> int:
        return sum(1 for m in self.matches if m.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for m in self.matches if m.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for m in self.matches if m.severity == Severity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for m in self.matches if m.severity == Severity.LOW)

    @property
    def max_cvss_score(self) -> float | None:
        scores = [m.cve.base_score for m in self.matches if m.cve.base_score is not None]
        return max(scores) if scores else None

    @property
    def max_risk_score(self) -> float:
        scores = [m.risk_score for m in self.matches]
        return max(scores) if scores else 0.0

    @property
    def has_exploitable_vulns(self) -> bool:
        return any(m.cve.has_public_exploit for m in self.matches)

    def sorted_by_risk(self) -> tuple[CorrelationMatch, ...]:
        return tuple(sorted(self.matches, key=lambda m: m.risk_score, reverse=True))

    def filtered_by_severity(self, *severities: Severity) -> tuple[CorrelationMatch, ...]:
        return tuple(m for m in self.matches if m.severity in severities)
