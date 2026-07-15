"""
Anthropic Claude AI provider for vulnerability remediation recommendations.
Implements structured prompting for consistent, actionable security advice.
"""
from __future__ import annotations

from typing import Any

import anthropic
import structlog

from app.config import get_settings
from app.domain.exceptions import AnthropicAPIError

logger = structlog.get_logger(__name__)

_REMEDIATION_SYSTEM_PROMPT = """You are a senior cybersecurity engineer providing remediation guidance for vulnerabilities discovered during security assessments. Your recommendations must be:

1. **Specific and actionable** - Provide exact commands, configuration changes, or code snippets where possible
2. **Prioritized** - Order steps from most critical to least
3. **Contextual** - Consider the service, version, and operating system when known
4. **Risk-aware** - Note any risks associated with applying fixes (e.g., service restarts, breaking changes)
5. **Verification-included** - Include how to verify the fix was applied successfully

Always structure your response as valid JSON matching this schema:
{
  "summary": "One-sentence summary of the remediation",
  "severity_assessment": "Brief assessment of the actual risk in context",
  "immediate_steps": [
    {
      "step": 1,
      "title": "Step title",
      "description": "Detailed description",
      "commands": ["command1", "command2"],
      "expected_output": "What success looks like"
    }
  ],
  "long_term_recommendations": ["recommendation1", "recommendation2"],
  "verification_steps": ["How to verify the fix"],
  "references": ["CVE link", "vendor advisory", "patch URL"],
  "estimated_effort": "15 minutes | 1 hour | 4 hours | 1 day | 1 week",
  "requires_restart": true,
  "confidence": 0.95
}

Return ONLY the JSON object. No markdown, no preamble, no explanation outside the JSON."""


class ClaudeAIProvider:
    """
    Anthropic Claude provider for AI-powered remediation recommendations.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)

    async def generate_remediation(
        self,
        vulnerability_title: str,
        cve_id: str | None,
        cvss_score: float | None,
        severity: str,
        description: str,
        affected_service: str | None,
        affected_port: int | None,
        asset_os: str | None,
        asset_hostname: str | None,
        organization_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate AI-powered remediation recommendation for a vulnerability.

        Returns structured remediation plan with steps, commands, and verification.
        """
        prompt = self._build_prompt(
            title=vulnerability_title,
            cve_id=cve_id,
            cvss_score=cvss_score,
            severity=severity,
            description=description,
            service=affected_service,
            port=affected_port,
            os=asset_os,
            hostname=asset_hostname,
        )

        logger.info(
            "claude_remediation_request",
            cve_id=cve_id,
            severity=severity,
            service=affected_service,
        )

        try:
            # Note: anthropic client is sync; wrap in executor for async context
            import asyncio

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.messages.create(
                    model=self._settings.anthropic_model,
                    max_tokens=self._settings.anthropic_max_tokens,
                    system=_REMEDIATION_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                ),
            )
        except anthropic.RateLimitError as e:
            raise AnthropicAPIError(f"Rate limit exceeded: {e}", status_code=429) from e
        except anthropic.APIStatusError as e:
            raise AnthropicAPIError(
                f"API error {e.status_code}: {e.message}", status_code=e.status_code
            ) from e
        except anthropic.APIConnectionError as e:
            raise AnthropicAPIError(f"Connection error: {e}") from e

        raw_content = response.content[0].text if response.content else ""

        # Parse structured JSON response
        import json
        try:
            structured = json.loads(raw_content)
        except json.JSONDecodeError:
            # Fallback: wrap raw content in minimal structure
            logger.warning("claude_non_json_response", content_preview=raw_content[:200])
            structured = {
                "summary": "See full recommendation below",
                "immediate_steps": [],
                "long_term_recommendations": [raw_content],
                "verification_steps": [],
                "references": [],
                "estimated_effort": "unknown",
                "requires_restart": False,
                "confidence": 0.5,
            }

        return {
            "ai_model": self._settings.anthropic_model,
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "recommendation_markdown": self._to_markdown(structured),
            "structured_steps": structured,
            "confidence_score": structured.get("confidence", 0.8),
        }

    async def generate_executive_summary(
        self,
        org_name: str,
        health_score: int,
        total_assets: int,
        vuln_counts: dict[str, int],
        top_vulnerabilities: list[dict[str, Any]],
    ) -> str:
        """Generate an executive summary for security reports."""
        prompt = f"""Generate an executive security summary for {org_name}.

Security Health Score: {health_score}/100
Total Assets Assessed: {total_assets}
Vulnerability Breakdown:
- Critical: {vuln_counts.get('critical', 0)}
- High: {vuln_counts.get('high', 0)}
- Medium: {vuln_counts.get('medium', 0)}
- Low: {vuln_counts.get('low', 0)}

Top 5 Vulnerabilities:
{self._format_top_vulns(top_vulnerabilities)}

Write a 3-paragraph executive summary suitable for a non-technical audience that:
1. States the overall security posture
2. Highlights the most critical risks and their business impact
3. Recommends immediate priorities

Be direct, avoid jargon, use business language."""

        import asyncio

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.messages.create(
                    model=self._settings.anthropic_model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                ),
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            logger.error("claude_executive_summary_failed", error=str(e))
            return "Executive summary generation failed. Please review the technical findings below."

    def _build_prompt(
        self,
        title: str,
        cve_id: str | None,
        cvss_score: float | None,
        severity: str,
        description: str,
        service: str | None,
        port: int | None,
        os: str | None,
        hostname: str | None,
    ) -> str:
        context_parts = [
            f"**Vulnerability**: {title}",
            f"**CVE ID**: {cve_id or 'N/A'}",
            f"**CVSS Score**: {cvss_score or 'N/A'} ({severity.upper()})",
            f"**Description**: {description}",
        ]

        if service:
            context_parts.append(f"**Affected Service**: {service}")
        if port:
            context_parts.append(f"**Port**: {port}")
        if os:
            context_parts.append(f"**Operating System**: {os}")
        if hostname:
            context_parts.append(f"**Hostname**: {hostname}")

        return (
            "Provide remediation guidance for the following vulnerability:\n\n"
            + "\n".join(context_parts)
        )

    @staticmethod
    def _format_top_vulns(vulns: list[dict[str, Any]]) -> str:
        lines = []
        for i, v in enumerate(vulns[:5], 1):
            lines.append(
                f"{i}. [{v.get('severity', '').upper()}] {v.get('title', 'Unknown')} "
                f"(CVSS: {v.get('cvss_score', 'N/A')})"
            )
        return "\n".join(lines)

    @staticmethod
    def _to_markdown(structured: dict[str, Any]) -> str:
        """Convert structured JSON remediation to readable Markdown."""
        lines = []

        if summary := structured.get("summary"):
            lines.append(f"## Summary\n{summary}\n")

        if assessment := structured.get("severity_assessment"):
            lines.append(f"## Risk Assessment\n{assessment}\n")

        if steps := structured.get("immediate_steps", []):
            lines.append("## Immediate Remediation Steps\n")
            for step in steps:
                lines.append(f"### Step {step.get('step', '')}: {step.get('title', '')}")
                lines.append(step.get("description", ""))
                if cmds := step.get("commands", []):
                    lines.append("```bash")
                    lines.extend(cmds)
                    lines.append("```")
                if expected := step.get("expected_output"):
                    lines.append(f"**Expected Output**: {expected}")
                lines.append("")

        if lt_recs := structured.get("long_term_recommendations", []):
            lines.append("## Long-Term Recommendations\n")
            for rec in lt_recs:
                lines.append(f"- {rec}")
            lines.append("")

        if verification := structured.get("verification_steps", []):
            lines.append("## Verification\n")
            for step in verification:
                lines.append(f"- {step}")
            lines.append("")

        if refs := structured.get("references", []):
            lines.append("## References\n")
            for ref in refs:
                lines.append(f"- {ref}")

        effort = structured.get("estimated_effort", "Unknown")
        restart = "Yes" if structured.get("requires_restart") else "No"
        lines.append(f"\n---\n**Estimated Effort**: {effort} | **Requires Restart**: {restart}")

        return "\n".join(lines)
