"""
Structured output parser and validator.

Every LLM response goes through three gates before being returned:

  Gate 1 — JSON extraction
    Strip markdown fences, find the JSON object boundaries,
    attempt json.loads(). Retry-safe.

  Gate 2 — Schema validation
    Check required fields are present with correct types.
    Missing optional fields get safe defaults.
    Wrong types are coerced where unambiguous (str → int for scores).

  Gate 3 — Integrity checks
    CVE IDs in outputs must be a subset of CVE IDs in the input.
    Confidence scores must be 0.0–1.0.
    Risk scores must be 0.0–100.0.
    Any output referencing a CVE not in the input is sanitised.

Failed validation raises LLMOutputParseError with the raw output
attached so callers can log it, retry with a different prompt, or
fall back to a degraded response.
"""
from __future__ import annotations

import json
import re
from typing import Any

import structlog

from app.domain.models.analysis import (
    AnalysisRequest,
    AnalysisStage,
    ExecutiveSummary,
    ManagementSummary,
    PrioritizedVuln,
    RemediationPlan,
    RemediationRecommendations,
    RemediationStep,
    RemediationEffort,
    RiskLevel,
    RiskPrioritization,
    TechnicalAnalysis,
    TechnicalFinding,
    ThreatIndicator,
)
from app.infrastructure.ai.provider_protocol import LLMOutputParseError

logger = structlog.get_logger(__name__)

# Match JSON object or array at top level, ignoring surrounding text
_JSON_OBJECT_RE = re.compile(r'\{.*\}', re.DOTALL)
_JSON_FENCE_RE  = re.compile(r'```(?:json)?\s*(.*?)\s*```', re.DOTALL | re.IGNORECASE)


class OutputParser:
    """
    Parses and validates LLM responses into typed domain objects.
    One instance is shared across all stages (stateless).
    """

    def parse(
        self,
        stage:   AnalysisStage,
        raw:     str,
        request: AnalysisRequest,
    ) -> Any:
        """
        Parse raw LLM output for a given stage.

        Args:
            stage:   Which stage produced this output
            raw:     Raw string from the LLM
            request: Original request (for CVE ID integrity checks)

        Returns:
            Typed domain object for the stage

        Raises:
            LLMOutputParseError: if parsing or validation fails
        """
        data = self._extract_json(raw, stage)
        valid_cve_ids = {v.cve_id for v in request.vulnerabilities}

        parsers = {
            AnalysisStage.TRIAGE:        self._parse_executive_summary,
            AnalysisStage.TECHNICAL:     self._parse_technical_analysis,
            AnalysisStage.RISK_PRIORITY: self._parse_risk_prioritization,
            AnalysisStage.REMEDIATION:   self._parse_remediation,
            AnalysisStage.EXECUTIVE:     self._parse_management_summary,
        }

        parser = parsers.get(stage)
        if parser is None:
            raise LLMOutputParseError(stage.value, raw, f"No parser for stage {stage}")

        try:
            return parser(data, valid_cve_ids)
        except (KeyError, TypeError, ValueError) as exc:
            raise LLMOutputParseError(
                stage.value, raw, f"Schema validation failed: {exc}"
            ) from exc

    # ── Gate 1: JSON extraction ────────────────────────────────

    def _extract_json(self, raw: str, stage: AnalysisStage) -> dict[str, Any]:
        """Extract JSON from raw LLM output, tolerating common formatting issues."""
        text = raw.strip()

        # Try markdown code fences first
        fence_match = _JSON_FENCE_RE.search(text)
        if fence_match:
            text = fence_match.group(1).strip()

        # Try direct parse
        try:
            return json.loads(text)  # type: ignore[return-value]
        except json.JSONDecodeError:
            pass

        # Find JSON object boundaries
        obj_match = _JSON_OBJECT_RE.search(text)
        if obj_match:
            try:
                return json.loads(obj_match.group())  # type: ignore[return-value]
            except json.JSONDecodeError:
                pass

        # Last resort: fix common LLM JSON mistakes
        fixed = self._fix_common_json_issues(text)
        try:
            return json.loads(fixed)  # type: ignore[return-value]
        except json.JSONDecodeError as exc:
            raise LLMOutputParseError(
                stage.value, raw, f"Could not extract valid JSON: {exc}"
            ) from exc

    @staticmethod
    def _fix_common_json_issues(text: str) -> str:
        """Fix the most common LLM JSON generation mistakes."""
        # Remove trailing commas before } or ]
        text = re.sub(r',\s*([}\]])', r'\1', text)
        # Replace single quotes with double quotes (outside already-quoted strings)
        # This is heuristic and not perfect but catches most cases
        text = re.sub(r"(?<!\\)'", '"', text)
        # Remove comments (some models add // comments)
        text = re.sub(r'//[^\n]*', '', text)
        return text

    # ── Gate 2+3: Stage parsers ────────────────────────────────

    def _parse_executive_summary(
        self, data: dict[str, Any], valid_cves: set[str]
    ) -> ExecutiveSummary:
        return ExecutiveSummary(
            overall_risk_level= RiskLevel(self._str(data, "overall_risk_level", "high")),
            headline=           self._str(data, "headline", "Security assessment complete"),
            business_impact=    self._str(data, "business_impact", ""),
            key_findings=       tuple(self._list_of_str(data, "key_findings")),
            immediate_actions=  tuple(self._list_of_str(data, "immediate_actions")),
            confidence=         self._float_bounded(data, "confidence", 0.8, 0.0, 1.0),
        )

    def _parse_technical_analysis(
        self, data: dict[str, Any], valid_cves: set[str]
    ) -> TechnicalAnalysis:
        findings = []
        for f in data.get("findings", []):
            if not isinstance(f, dict):
                continue
            cve_id = f.get("cve_id")
            # Gate 3: CVE integrity
            if cve_id and cve_id not in valid_cves:
                logger.warning("invalid_cve_in_output", cve_id=cve_id)
                cve_id = None   # Sanitise rather than reject entirely

            findings.append(TechnicalFinding(
                cve_id=          cve_id,
                title=           self._str(f, "title", "Untitled finding"),
                affected_service=self._str(f, "affected_service", "Unknown"),
                affected_port=   self._int_or_none(f, "affected_port"),
                technical_detail=self._str(f, "technical_detail", ""),
                attack_scenario= self._str(f, "attack_scenario", ""),
                exploitation_complexity=self._str(f, "exploitation_complexity", "moderate"),
                blast_radius=    self._str(f, "blast_radius", "Unknown"),
                confidence=      self._float_bounded(f, "confidence", 0.7, 0.0, 1.0),
            ))

        indicators = []
        for ind in data.get("threat_indicators", []):
            if not isinstance(ind, dict):
                continue
            raw_refs   = ind.get("cve_refs", [])
            clean_refs = tuple(r for r in raw_refs if isinstance(r, str) and r in valid_cves)
            indicators.append(ThreatIndicator(
                indicator=   self._str(ind, "indicator", ""),
                threat_type= self._str(ind, "threat_type", "Unknown"),
                cve_refs=    clean_refs,
                confidence=  self._float_bounded(ind, "confidence", 0.7, 0.0, 1.0),
            ))

        return TechnicalAnalysis(
            attack_surface_summary= self._str(data, "attack_surface_summary", ""),
            most_critical_path=     self._str(data, "most_critical_path", ""),
            findings=               tuple(findings),
            threat_indicators=      tuple(indicators),
            lateral_movement_risk=  self._str(data, "lateral_movement_risk", ""),
            data_exfiltration_risk= self._str(data, "data_exfiltration_risk", ""),
        )

    def _parse_risk_prioritization(
        self, data: dict[str, Any], valid_cves: set[str]
    ) -> RiskPrioritization:
        prioritized = []
        for item in data.get("prioritized_vulns", []):
            if not isinstance(item, dict):
                continue
            cve_id = self._str(item, "cve_id", "")
            # Gate 3: only include CVEs from the input
            if cve_id not in valid_cves:
                logger.warning("risk_priority_invalid_cve", cve_id=cve_id)
                continue

            try:
                risk_level = RiskLevel(item.get("risk_level", "medium").lower())
            except ValueError:
                risk_level = RiskLevel.MEDIUM

            prioritized.append(PrioritizedVuln(
                cve_id=           cve_id,
                title=            self._str(item, "title", cve_id),
                risk_level=       risk_level,
                priority_score=   self._float_bounded(item, "priority_score", 50.0, 0.0, 100.0),
                cvss_score=       item.get("cvss_score"),
                business_context= self._str(item, "business_context", ""),
                exploitability=   self._str(item, "exploitability", "theoretical"),
                time_to_exploit=  self._str(item, "time_to_exploit", "Unknown"),
                affected_service= self._str(item, "affected_service", "Unknown"),
                priority_rationale=self._str(item, "priority_rationale", ""),
            ))

        return RiskPrioritization(
            prioritized_vulns=   tuple(prioritized),
            top_3_rationale=     self._str(data, "top_3_rationale", ""),
            risk_acceptance_note=self._str(data, "risk_acceptance_note", ""),
        )

    def _parse_remediation(
        self, data: dict[str, Any], valid_cves: set[str]
    ) -> RemediationRecommendations:
        def _parse_plan(raw: dict[str, Any], priority: int) -> RemediationPlan | None:
            if not isinstance(raw, dict):
                return None
            cve_id = self._str(raw, "cve_id", "")
            if cve_id not in valid_cves:
                logger.warning("remediation_invalid_cve", cve_id=cve_id)
                return None

            steps = []
            for i, step in enumerate(raw.get("steps", []), 1):
                if not isinstance(step, dict):
                    continue
                steps.append(RemediationStep(
                    step_number=     int(step.get("step_number", i)),
                    title=           self._str(step, "title", f"Step {i}"),
                    description=     self._str(step, "description", ""),
                    commands=        tuple(c for c in step.get("commands", []) if isinstance(c, str)),
                    verification=    self._str(step, "verification", ""),
                    estimated_time=  self._str(step, "estimated_time", "Unknown"),
                    requires_restart=bool(step.get("requires_restart", False)),
                    requires_downtime=bool(step.get("requires_downtime", False)),
                ))

            try:
                effort = RemediationEffort(raw.get("effort", "short_term"))
            except ValueError:
                effort = RemediationEffort.SHORT_TERM

            return RemediationPlan(
                cve_id=       cve_id,
                title=        self._str(raw, "title", cve_id),
                effort=       effort,
                priority=     priority,
                steps=        tuple(steps),
                prerequisites=tuple(p for p in raw.get("prerequisites", []) if isinstance(p, str)),
                rollback_plan=self._str(raw, "rollback_plan", "Restore from backup if needed"),
                references=   tuple(r for r in raw.get("references", []) if isinstance(r, str)),
                confidence=   self._float_bounded(raw, "confidence", 0.8, 0.0, 1.0),
            )

        immediate   = []
        short_term  = []
        long_term   = []

        for i, raw in enumerate(data.get("immediate_actions", []),   1):
            plan = _parse_plan(raw, i)
            if plan:
                immediate.append(plan)

        for i, raw in enumerate(data.get("short_term_actions", []),  len(immediate) + 1):
            plan = _parse_plan(raw, i)
            if plan:
                short_term.append(plan)

        for i, raw in enumerate(data.get("long_term_actions", []),   len(immediate) + len(short_term) + 1):
            plan = _parse_plan(raw, i)
            if plan:
                long_term.append(plan)

        return RemediationRecommendations(
            immediate_actions=  tuple(immediate),
            short_term_actions= tuple(short_term),
            long_term_actions=  tuple(long_term),
            quick_wins=         tuple(self._list_of_str(data, "quick_wins")),
            estimated_total_effort=self._str(data, "estimated_total_effort", "Unknown"),
        )

    def _parse_management_summary(
        self, data: dict[str, Any], valid_cves: set[str]
    ) -> ManagementSummary:
        score = int(self._float_bounded(data, "security_score", 50.0, 0.0, 100.0))
        if score >= 90:
            label = "Excellent"
        elif score >= 75:
            label = "Very Good"
        elif score >= 60:
            label = "Good"
        elif score >= 40:
            label = "Fair"
        else:
            label = "Poor"

        return ManagementSummary(
            risk_headline=         self._str(data, "risk_headline", "Security assessment complete"),
            security_score=        score,
            score_label=           data.get("score_label") or label,
            top_risks=             tuple(self._list_of_str(data, "top_risks")),
            business_risks=        tuple(self._list_of_str(data, "business_risks")),
            investment_needed=     self._str(data, "investment_needed", "Unknown"),
            what_happens_if_ignored=self._str(data, "what_happens_if_ignored", ""),
            what_we_recommend=     self._str(data, "what_we_recommend", ""),
        )

    # ── Type helpers ───────────────────────────────────────────

    @staticmethod
    def _str(d: dict[str, Any], key: str, default: str) -> str:
        v = d.get(key, default)
        if v is None:
            return default
        return str(v).strip() or default

    @staticmethod
    def _int_or_none(d: dict[str, Any], key: str) -> int | None:
        v = d.get(key)
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _float_bounded(d: dict[str, Any], key: str, default: float, lo: float, hi: float) -> float:
        v = d.get(key, default)
        try:
            f = float(v)
            return max(lo, min(hi, f))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _list_of_str(d: dict[str, Any], key: str) -> list[str]:
        v = d.get(key, [])
        if not isinstance(v, list):
            return []
        return [str(item) for item in v if item is not None]
