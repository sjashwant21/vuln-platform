"""
Prompt engineering for the AI Security Analyst.

Design decisions:
  1. System prompts encode a specific expert persona and reasoning framework
  2. User prompts contain ONLY structured facts from our data — never free text
     from untrusted sources (asset names, banners) without sanitisation
  3. Every prompt includes explicit anti-hallucination instructions:
       - "Only reference CVEs from the provided list"
       - "If you are uncertain, say so explicitly"
       - "Do not invent patch versions or remediation steps not in references"
  4. JSON schema is embedded in the system prompt so the model knows
     exactly what structure to produce
  5. Chain-of-thought is elicited with "Think step by step" in analytical stages
  6. Temperature 0.1 enforced in config — determinism over creativity
"""
from __future__ import annotations

import json
from datetime import datetime

from app.domain.models.analysis import AnalysisRequest, AnalysisStage


# ══════════════════════════════════════════════════════════════════
# Shared analyst persona (prepended to every system prompt)
# ══════════════════════════════════════════════════════════════════

_ANALYST_PERSONA = """You are an elite cybersecurity analyst with 15+ years of experience in:
- Penetration testing and red team operations
- Vulnerability assessment and threat modelling
- Incident response and forensic analysis
- Security architecture review
- Risk quantification for enterprise environments

Your analysis is used by security engineers, CISOs, and executive leadership.
You are known for being precise, evidence-based, and practical.

CRITICAL RULES — violations will invalidate your analysis:
1. ONLY reference CVE IDs that appear in the provided vulnerability list
2. ONLY make claims you can directly support from the provided data
3. If you are uncertain about something, say so explicitly with a confidence score below 0.7
4. Do not invent specific version numbers, patch releases, or commands not in the data
5. Do not reference exploits, tools, or techniques not directly relevant to the provided CVEs
6. Every technical claim must be traceable to a specific CVE or service in the input
7. Attack scenarios must be realistic given the actual services and versions present"""

_JSON_INSTRUCTION = """
Respond with a single valid JSON object matching the schema provided.
No markdown code fences. No preamble. No explanation outside the JSON.
Start your response with { and end with }."""


# ══════════════════════════════════════════════════════════════════
# Input serialiser — converts AnalysisRequest to structured text
# ══════════════════════════════════════════════════════════════════

class PromptBuilder:
    """
    Builds prompts for each analysis stage.

    Each stage receives:
      - A system prompt with the analyst persona + task instructions + JSON schema
      - A user prompt with the structured vulnerability data

    The system/user split is intentional:
      - System prompt is stable and cacheable (providers cache system prompts)
      - User prompt changes per request
    """

    def build(
        self,
        stage:   AnalysisStage,
        request: AnalysisRequest,
        prior_outputs: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        """
        Build (system_prompt, user_prompt) for a given analysis stage.

        Args:
            stage:         Which analysis stage to build prompts for
            request:       The full analysis request with asset and vuln data
            prior_outputs: JSON outputs from earlier stages (for chaining)

        Returns:
            (system_prompt, user_prompt) tuple
        """
        data_block = self._serialise_request(request)

        builders = {
            AnalysisStage.TRIAGE:        self._executive_summary_prompts,
            AnalysisStage.TECHNICAL:     self._technical_analysis_prompts,
            AnalysisStage.RISK_PRIORITY: self._risk_prioritization_prompts,
            AnalysisStage.REMEDIATION:   self._remediation_prompts,
            AnalysisStage.EXECUTIVE:     self._management_summary_prompts,
        }

        builder = builders.get(stage)
        if builder is None:
            raise ValueError(f"No prompt builder for stage: {stage}")

        return builder(data_block, prior_outputs or {})

    # ── Stage 1: Executive Summary ─────────────────────────────

    def _executive_summary_prompts(
        self,
        data_block:    str,
        prior_outputs: dict[str, str],
    ) -> tuple[str, str]:
        schema = json.dumps({
            "overall_risk_level": "critical|high|medium|low|info",
            "headline": "One sentence — the single most important finding",
            "business_impact": "2-3 sentences. What could go wrong for the business? Use plain language, no CVE IDs.",
            "key_findings": [
                "Finding 1 in plain language (no CVE IDs, no technical jargon)",
                "Finding 2...",
                "Finding 3...",
                "Finding 4 (optional)",
                "Finding 5 (optional)"
            ],
            "immediate_actions": [
                "Specific action that must happen TODAY",
                "Another immediate action (max 3)"
            ],
            "confidence": 0.95
        }, indent=2)

        system = f"""{_ANALYST_PERSONA}

YOUR TASK — EXECUTIVE SUMMARY:
Produce a concise executive summary of the security assessment findings.
This will be read by the CEO/CTO/Board — assume zero technical knowledge.

Rules for this summary:
- No CVE IDs, CVSS scores, or technical identifiers in the output
- No jargon: "remote code execution" → "an attacker can run commands on your server"
- Frame everything in business terms: revenue impact, reputation, compliance, operations
- The headline must be a single sentence anyone can understand
- Key findings must be concrete, not vague ("An attacker can steal customer data" not "Data exfiltration risk")
- Immediate actions must be specific enough for a manager to delegate

Think step by step:
1. What is the worst thing that could happen to this business based on these findings?
2. Which findings have the highest likelihood of being exploited?
3. What would a non-technical executive need to know to make a budget/priority decision?

{_JSON_INSTRUCTION}

JSON SCHEMA:
{schema}"""

        user = f"""SECURITY ASSESSMENT DATA:

{data_block}

Produce the executive summary JSON now."""

        return system, user

    # ── Stage 2: Technical Analysis ────────────────────────────

    def _technical_analysis_prompts(
        self,
        data_block:    str,
        prior_outputs: dict[str, str],
    ) -> tuple[str, str]:
        schema = json.dumps({
            "attack_surface_summary": "2-3 sentences describing the exposed attack surface",
            "most_critical_path": "Narrative description of the highest-risk attack chain from external attacker to worst outcome",
            "findings": [
                {
                    "cve_id": "CVE-YYYY-NNNNN or null for non-CVE findings",
                    "title": "Short descriptive title",
                    "affected_service": "service name",
                    "affected_port": 443,
                    "technical_detail": "Deep technical explanation for security engineers",
                    "attack_scenario": "Step-by-step: 1. Attacker scans... 2. Attacker exploits... 3. Attacker achieves...",
                    "exploitation_complexity": "trivial|moderate|complex",
                    "blast_radius": "What an attacker gains: e.g., 'full root access to the server, access to internal network'",
                    "confidence": 0.9
                }
            ],
            "threat_indicators": [
                {
                    "indicator": "What was observed",
                    "threat_type": "e.g. Remote Code Execution, Privilege Escalation",
                    "cve_refs": ["CVE-YYYY-NNNNN"],
                    "confidence": 0.85
                }
            ],
            "lateral_movement_risk": "Assessment of attacker's ability to move through the network after initial compromise",
            "data_exfiltration_risk": "Assessment of what data could be stolen and how"
        }, indent=2)

        system = f"""{_ANALYST_PERSONA}

YOUR TASK — TECHNICAL ANALYSIS:
Produce a deep technical analysis for security engineers who will act on these findings.

Rules:
- Every finding's cve_id MUST appear in the input vulnerability list (or be null)
- Attack scenarios must be realistic given the actual service versions present
- exploitation_complexity must reflect real-world exploitation, not just CVSS
- blast_radius must be specific to this asset's role and criticality
- Do not reference CVEs, exploits, or tools not in the provided data

Think step by step:
1. Which vulnerabilities are most likely to be chained together?
2. What is the realistic attack path from internet to maximum impact?
3. What does post-exploitation look like on this specific asset?
4. Which findings are high CVSS but low real-world risk (and why)?

{_JSON_INSTRUCTION}

JSON SCHEMA:
{schema}"""

        user = f"""SECURITY ASSESSMENT DATA:

{data_block}

Produce the technical analysis JSON now."""

        return system, user

    # ── Stage 3: Risk Prioritization ───────────────────────────

    def _risk_prioritization_prompts(
        self,
        data_block:    str,
        prior_outputs: dict[str, str],
    ) -> tuple[str, str]:
        prior_context = ""
        if "executive" in prior_outputs:
            prior_context = f"\nEXECUTIVE SUMMARY (for context):\n{prior_outputs['executive']}\n"

        schema = json.dumps({
            "prioritized_vulns": [
                {
                    "cve_id": "CVE-YYYY-NNNNN — MUST be from input list",
                    "title": "Vulnerability title",
                    "risk_level": "critical|high|medium|low",
                    "priority_score": 87.5,
                    "cvss_score": 9.8,
                    "business_context": "Why this matters to the business specifically",
                    "exploitability": "actively exploited|poc available|theoretical",
                    "time_to_exploit": "e.g. '15 minutes with public tools' or '2-4 hours for skilled attacker'",
                    "affected_service": "service name and port",
                    "priority_rationale": "One sentence: why this is ranked here vs others"
                }
            ],
            "top_3_rationale": "Explanation of why the top 3 are most urgent, beyond just their CVSS scores",
            "risk_acceptance_note": "What it means in practical terms to defer action on the lower-priority items"
        }, indent=2)

        system = f"""{_ANALYST_PERSONA}

YOUR TASK — RISK PRIORITIZATION:
Re-order vulnerabilities by actual business risk, NOT by CVSS score alone.

CVSS measures intrinsic severity. Risk = Severity × Likelihood × Business Impact.
A CVSS 9.8 with no public exploit on an internal dev server may rank below
a CVSS 7.5 with an active exploit kit on an internet-facing production server.

Prioritization factors (in order of importance):
1. Is there a public exploit or active exploitation in the wild?
2. Is the asset internet-facing?
3. What is the asset's criticality to the business?
4. How many steps does exploitation require?
5. What is the blast radius if exploited?
6. Can it be chained with other vulnerabilities?
7. CVSS score (important but not decisive)

Rules:
- Every cve_id MUST appear in the input vulnerability list
- priority_score is 0-100 (your composite score, not CVSS)
- Be explicit when you deviate from CVSS order and why
- Do not create new vulnerabilities not in the input

{_JSON_INSTRUCTION}

JSON SCHEMA:
{schema}"""

        user = f"""SECURITY ASSESSMENT DATA:

{data_block}
{prior_context}
Produce the risk prioritization JSON now. Order vulnerabilities by actual business risk."""

        return system, user

    # ── Stage 4: Remediation ───────────────────────────────────

    def _remediation_prompts(
        self,
        data_block:    str,
        prior_outputs: dict[str, str],
    ) -> tuple[str, str]:
        prior_context = ""
        if "risk_priority" in prior_outputs:
            prior_context = (
                f"\nRISK PRIORITIZATION (use this order for remediation priority):\n"
                f"{prior_outputs['risk_priority']}\n"
            )

        schema = json.dumps({
            "immediate_actions": [
                {
                    "cve_id": "CVE-YYYY-NNNNN — MUST be from input list",
                    "title": "What needs to be done",
                    "effort": "immediate|short_term|medium_term|long_term",
                    "priority": 1,
                    "steps": [
                        {
                            "step_number": 1,
                            "title": "Step title",
                            "description": "Detailed description",
                            "commands": ["exact command 1", "exact command 2"],
                            "verification": "How to verify this step worked",
                            "estimated_time": "15 minutes",
                            "requires_restart": False,
                            "requires_downtime": False
                        }
                    ],
                    "prerequisites": ["What must be done before this"],
                    "rollback_plan": "How to undo this if it breaks something",
                    "references": ["https://vendor.com/advisory", "https://cve.mitre.org/..."],
                    "confidence": 0.9
                }
            ],
            "short_term_actions": [],
            "long_term_actions": [],
            "quick_wins": [
                "Action that takes < 30 minutes and significantly reduces risk"
            ],
            "estimated_total_effort": "e.g. '3 engineer-days to address all critical/high findings'"
        }, indent=2)

        system = f"""{_ANALYST_PERSONA}

YOUR TASK — REMEDIATION RECOMMENDATIONS:
Produce specific, actionable remediation steps that a sysadmin can execute.

Rules for remediation steps:
- Commands must be real, syntactically correct commands for the identified OS/service
- Do not invent patch versions — only reference patches mentioned in the CVE references
- If you don't know the exact command, say "Consult vendor documentation at [URL]"
- Steps must be in the correct dependency order (patch before restart, backup before patch)
- Rollback plan is mandatory for any change that could cause downtime
- Every cve_id MUST be from the input vulnerability list

Classify actions as:
  immediate   = Must happen today (critical vulnerabilities with public exploits)
  short_term  = This week (high severity, no active exploit)
  medium_term = This month (medium severity or requires planning)
  long_term   = This quarter (low severity or requires architectural change)

For commands, tailor to the detected OS if available. If OS is unknown,
provide both Linux and Windows variants where they differ.

{_JSON_INSTRUCTION}

JSON SCHEMA:
{schema}"""

        user = f"""SECURITY ASSESSMENT DATA:

{data_block}
{prior_context}
Produce the remediation recommendations JSON now."""

        return system, user

    # ── Stage 5: Management Summary ────────────────────────────

    def _management_summary_prompts(
        self,
        data_block:    str,
        prior_outputs: dict[str, str],
    ) -> tuple[str, str]:
        # This stage synthesises all prior stages
        synthesis = "\n".join(
            f"\n{stage.upper()} ANALYSIS:\n{output}"
            for stage, output in prior_outputs.items()
        )

        schema = json.dumps({
            "risk_headline":   "One sentence a non-technical manager can repeat to their board",
            "security_score":  72,
            "score_label":     "Fair",
            "top_risks": [
                "Risk 1 in plain English — what could happen and to what",
                "Risk 2...",
                "Risk 3 (max 5 total)"
            ],
            "business_risks": [
                "Compliance: e.g. 'This configuration violates PCI-DSS requirement 6.3.3'",
                "Financial: e.g. 'A breach could result in regulatory fines up to $X'",
                "Reputational: e.g. 'Customer data exposure would require public disclosure'"
            ],
            "investment_needed":      "e.g. '2 engineer-days + $0 in software costs'",
            "what_happens_if_ignored":"Clear statement of the consequence of inaction",
            "what_we_recommend":      "Single paragraph: the recommended course of action and expected outcome"
        }, indent=2)

        system = f"""{_ANALYST_PERSONA}

YOUR TASK — MANAGEMENT SUMMARY:
Produce a one-page summary for non-technical executives and board members.

This document will be used to:
- Justify security investment to finance/leadership
- Communicate risk to the board
- Set remediation priorities for the next sprint/quarter

Rules:
- Zero technical jargon — explain every concept in business terms
- security_score is your holistic assessment (0=catastrophic, 100=excellent)
- score_label: 0-39=Poor, 40-59=Fair, 60-74=Good, 75-89=Very Good, 90-100=Excellent
- business_risks must be concrete and credible — no vague "reputational damage"
- investment_needed must be realistic based on the remediation steps
- what_happens_if_ignored must be specific, not generic
- Do not use CVE IDs in this output — translate them to plain language

{_JSON_INSTRUCTION}

JSON SCHEMA:
{schema}"""

        user = f"""COMPLETE SECURITY ANALYSIS:

{synthesis}

ORIGINAL ASSET DATA (for context):
{data_block}

Produce the management summary JSON now."""

        return system, user

    # ── Data serialiser ────────────────────────────────────────

    def _serialise_request(self, req: AnalysisRequest) -> str:
        """
        Convert AnalysisRequest to a structured text block for injection
        into LLM prompts. Format is chosen for readability by both humans
        and LLMs — not JSON (too verbose) or YAML (ambiguous types).
        """
        lines: list[str] = []

        # Asset context
        lines.append("=== ASSET INFORMATION ===")
        lines.append(f"Asset ID:          {req.asset_id}")
        lines.append(f"IP Address:        {req.asset_ip}")
        lines.append(f"Hostname:          {req.asset_hostname or 'Unknown'}")
        lines.append(f"Operating System:  {req.asset_os or 'Unknown'}")
        lines.append(f"Criticality:       {req.asset_criticality.upper()}")
        lines.append(f"Internet Exposed:  {'YES' if req.internet_exposed else 'NO'}")
        lines.append(f"Organisation:      {req.org_name}")
        lines.append(f"Scan Date:         {req.scan_date.strftime('%Y-%m-%d %H:%M UTC')}")
        if req.additional_context:
            lines.append(f"Analyst Notes:     {self._sanitise(req.additional_context)}")

        # Services
        lines.append("\n=== DETECTED SERVICES ===")
        if req.services:
            for svc in req.services:
                ver = f" {svc.version}" if svc.version else ""
                lines.append(f"  Port {svc.port}/{svc.protocol}: {svc.service}{ver}")
        else:
            lines.append("  No services detected")

        # Vulnerabilities
        lines.append(f"\n=== VULNERABILITIES ({len(req.vulnerabilities)} total) ===")
        for vuln in sorted(req.vulnerabilities, key=lambda v: v.cvss_score or 0, reverse=True):
            lines.append(f"\n  [{vuln.severity.upper()}] {vuln.cve_id}: {vuln.title}")
            lines.append(f"    CVSS Score:   {vuln.cvss_score or 'N/A'}")
            if vuln.cvss_vector:
                lines.append(f"    CVSS Vector:  {vuln.cvss_vector}")
            lines.append(f"    Service:      {vuln.service} (port {vuln.port or 'N/A'})")
            lines.append(f"    Affected Ver: {vuln.affected_version or 'Unknown'}")
            lines.append(f"    Public Exploit: {'YES — ACTIVELY EXPLOITABLE' if vuln.has_public_exploit else 'No known public exploit'}")
            lines.append(f"    Patch Available: {'YES' if vuln.has_patch else 'NO'}")
            lines.append(f"    Description:  {vuln.description[:300]}{'...' if len(vuln.description) > 300 else ''}")
            if vuln.references:
                lines.append(f"    References:   {'; '.join(vuln.references[:3])}")

        return "\n".join(lines)

    @staticmethod
    def _sanitise(text: str) -> str:
        """
        Strip characters that could break prompt structure or enable injection.
        We are injecting analyst notes (user-controlled) into a prompt —
        this must be treated as untrusted input.
        """
        # Remove prompt injection attempts
        dangerous_patterns = [
            "ignore previous instructions",
            "ignore all instructions",
            "you are now",
            "new instructions:",
            "system:",
            "</system",
            "<system",
        ]
        text_lower = text.lower()
        for pattern in dangerous_patterns:
            if pattern in text_lower:
                return "[REDACTED: Potentially unsafe content detected in analyst notes]"

        # Strip control characters, limit length
        sanitised = "".join(c for c in text if c.isprintable() or c in ("\n", "\t"))
        return sanitised[:500]
