"""
AI Security Analyst service — orchestrates the five-stage analysis pipeline.

Pipeline:
  Stage 1 (TRIAGE)        → ExecutiveSummary
  Stage 2 (TECHNICAL)     → TechnicalAnalysis
  Stage 3 (RISK_PRIORITY) → RiskPrioritization   [uses Stage 1 output]
  Stage 4 (REMEDIATION)   → RemediationRecommendations [uses Stage 3 output]
  Stage 5 (EXECUTIVE)     → ManagementSummary    [synthesises all prior stages]

Stages 1 and 2 run concurrently (they are independent).
Stages 3-5 run sequentially (each depends on prior output).

Retry strategy:
  - Each stage retries up to 2 times on parse failure
  - On second parse failure, a degraded placeholder is returned
    (the pipeline continues rather than failing entirely)
  - Provider errors (rate limit, timeout) propagate immediately

Token budget:
  - Each stage has its own max_tokens budget
  - Total token usage is tracked and returned in SecurityAnalysis metadata
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any

import structlog

from app.domain.models.analysis import (
    AnalysisRequest,
    AnalysisStage,
    ExecutiveSummary,
    ManagementSummary,
    ProviderConfig,
    RemediationRecommendations,
    RiskLevel,
    RiskPrioritization,
    SecurityAnalysis,
    TechnicalAnalysis,
)
from app.infrastructure.ai.output_parser import OutputParser
from app.infrastructure.ai.prompt_builder import PromptBuilder
from app.infrastructure.ai.provider_protocol import (
    LLMOutputParseError,
    LLMProviderError,
    LLMProviderProtocol,
    get_provider,
)

logger = structlog.get_logger(__name__)

# Per-stage token budgets — executive stages get more tokens for synthesis
_STAGE_TOKEN_BUDGETS: dict[AnalysisStage, int] = {
    AnalysisStage.TRIAGE:        1500,
    AnalysisStage.TECHNICAL:     3000,
    AnalysisStage.RISK_PRIORITY: 2000,
    AnalysisStage.REMEDIATION:   4096,
    AnalysisStage.EXECUTIVE:     2000,
}

_MAX_RETRIES = 2


class AIAnalystService:
    """
    Orchestrates the multi-stage AI security analysis pipeline.

    Injected at construction time with a provider — swapping
    Anthropic for OpenAI requires only changing ProviderConfig.
    """

    def __init__(
        self,
        provider:       LLMProviderProtocol,
        prompt_builder: PromptBuilder,
        output_parser:  OutputParser,
    ) -> None:
        self._provider = provider
        self._builder  = prompt_builder
        self._parser   = output_parser

    # ── Public interface ───────────────────────────────────────

    async def analyse(self, request: AnalysisRequest) -> SecurityAnalysis:
        """
        Run the full five-stage analysis pipeline.

        Raises:
            LLMProviderError: if the provider is unreachable
            LLMRateLimitError: if rate limited with no retry budget left
        """
        t0           = time.perf_counter()
        total_tokens = 0
        prior_outputs: dict[str, str] = {}

        logger.info(
            "analysis_start",
            asset_id=     request.asset_id,
            vuln_count=   len(request.vulnerabilities),
            provider=     self._provider.provider_name.value,
            model=        self._provider.model_name,
        )

        # ── Stages 1 + 2: Run concurrently ────────────────────
        triage_task   = asyncio.create_task(
            self._run_stage(AnalysisStage.TRIAGE, request, prior_outputs)
        )
        technical_task = asyncio.create_task(
            self._run_stage(AnalysisStage.TECHNICAL, request, prior_outputs)
        )

        (exec_summary, exec_tokens), (tech_analysis, tech_tokens) = await asyncio.gather(
            triage_task, technical_task
        )
        total_tokens += exec_tokens + tech_tokens

        # Store JSON representations for stage chaining
        prior_outputs["executive"] = self._to_json(exec_summary)
        prior_outputs["technical"] = self._to_json(tech_analysis)

        # ── Stage 3: Risk prioritization (uses stage 1 context) ─
        risk_result, risk_tokens = await self._run_stage(
            AnalysisStage.RISK_PRIORITY, request, prior_outputs
        )
        total_tokens += risk_tokens
        prior_outputs["risk_priority"] = self._to_json(risk_result)

        # ── Stage 4: Remediation (uses stage 3 ordering) ──────
        remediation_result, rem_tokens = await self._run_stage(
            AnalysisStage.REMEDIATION, request, prior_outputs
        )
        total_tokens += rem_tokens
        prior_outputs["remediation"] = self._to_json(remediation_result)

        # ── Stage 5: Management summary (synthesises all) ──────
        mgmt_result, mgmt_tokens = await self._run_stage(
            AnalysisStage.EXECUTIVE, request, prior_outputs
        )
        total_tokens += mgmt_tokens

        elapsed = time.perf_counter() - t0

        analysis = SecurityAnalysis(
            request=                     request,
            executive_summary=           exec_summary,       # type: ignore[arg-type]
            technical_analysis=          tech_analysis,      # type: ignore[arg-type]
            risk_prioritization=         risk_result,        # type: ignore[arg-type]
            remediation_recommendations= remediation_result, # type: ignore[arg-type]
            management_summary=          mgmt_result,        # type: ignore[arg-type]
            provider=                    self._provider.provider_name,
            model_name=                  self._provider.model_name,
            total_tokens=                total_tokens,
            analysis_time_s=             round(elapsed, 2),
            generated_at=                datetime.now(UTC),
        )

        logger.info(
            "analysis_complete",
            asset_id=     request.asset_id,
            total_tokens= total_tokens,
            elapsed_s=    round(elapsed, 2),
            risk_level=   analysis.executive_summary.overall_risk_level.value
            if hasattr(analysis.executive_summary, "overall_risk_level") else "unknown",
        )

        return analysis

    async def analyse_stream(
        self,
        request: AnalysisRequest,
        stage:   AnalysisStage = AnalysisStage.EXECUTIVE,
    ) -> Any:  # AsyncGenerator[str, None]
        """
        Stream the management summary as tokens arrive.
        Useful for real-time display in the UI while the full
        structured analysis completes in the background.
        """
        system_prompt, user_prompt = self._builder.build(stage, request)
        async for chunk in self._provider.stream(
            system_prompt=system_prompt,
            user_prompt=  user_prompt,
            max_tokens=   _STAGE_TOKEN_BUDGETS[stage],
        ):
            yield chunk

    # ── Stage runner with retry ────────────────────────────────

    async def _run_stage(
        self,
        stage:         AnalysisStage,
        request:       AnalysisRequest,
        prior_outputs: dict[str, str],
    ) -> tuple[Any, int]:
        """
        Run one analysis stage with retry on parse failure.

        Returns:
            (parsed_domain_object, tokens_used)
        """
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                system_prompt, user_prompt = self._builder.build(
                    stage, request, prior_outputs
                )

                response = await self._provider.complete(
                    system_prompt=system_prompt,
                    user_prompt=  user_prompt,
                    temperature=  0.1,
                    max_tokens=   _STAGE_TOKEN_BUDGETS[stage],
                    json_mode=    True,
                )

                tokens = response.prompt_tokens + response.completion_tokens

                if response.finish_reason == "length":
                    logger.warning(
                        "stage_truncated",
                        stage=stage.value,
                        max_tokens=_STAGE_TOKEN_BUDGETS[stage],
                    )

                result = self._parser.parse(stage, response.content, request)

                logger.debug(
                    "stage_complete",
                    stage=   stage.value,
                    tokens=  tokens,
                    attempt= attempt,
                )
                return result, tokens

            except LLMOutputParseError as exc:
                last_exc = exc
                logger.warning(
                    "stage_parse_retry",
                    stage=   stage.value,
                    attempt= attempt,
                    reason=  exc.reason,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue

            except LLMProviderError:
                raise   # Provider errors don't benefit from retry here

        # All retries exhausted — return degraded placeholder
        logger.error(
            "stage_failed_all_retries",
            stage=stage.value,
            error=str(last_exc),
        )
        return self._degraded_placeholder(stage, request), 0

    # ── Degraded placeholders ──────────────────────────────────

    def _degraded_placeholder(
        self, stage: AnalysisStage, request: AnalysisRequest
    ) -> Any:
        """
        Return a safe, clearly-marked placeholder when a stage fails.
        The pipeline continues — a partial analysis is better than no analysis.
        """

        note = "⚠️ Analysis for this section could not be completed. Please retry."

        if stage == AnalysisStage.TRIAGE:
            return ExecutiveSummary(
                overall_risk_level=RiskLevel.HIGH,
                headline=          note,
                business_impact=   note,
                key_findings=      (note,),
                immediate_actions= ("Retry the analysis or review findings manually.",),
                confidence=        0.0,
            )
        if stage == AnalysisStage.TECHNICAL:
            return TechnicalAnalysis(
                attack_surface_summary=  note,
                most_critical_path=      note,
                findings=                (),
                threat_indicators=       (),
                lateral_movement_risk=   note,
                data_exfiltration_risk=  note,
            )
        if stage == AnalysisStage.RISK_PRIORITY:
            return RiskPrioritization(
                prioritized_vulns=    (),
                top_3_rationale=      note,
                risk_acceptance_note= note,
            )
        if stage == AnalysisStage.REMEDIATION:
            return RemediationRecommendations(
                immediate_actions=      (),
                short_term_actions=     (),
                long_term_actions=      (),
                quick_wins=             (),
                estimated_total_effort= note,
            )
        return ManagementSummary(
            risk_headline=           note,
            security_score=          0,
            score_label=             "Unknown",
            top_risks=               (note,),
            business_risks=          (),
            investment_needed=       note,
            what_happens_if_ignored= note,
            what_we_recommend=       note,
        )

    @staticmethod
    def _to_json(obj: Any) -> str:
        """Serialise a domain object to JSON for stage chaining."""
        import dataclasses

        def _default(o: Any) -> Any:
            if dataclasses.is_dataclass(o) and not isinstance(o, type):
                return dataclasses.asdict(o)
            if hasattr(o, "value"):
                return o.value
            return str(o)

        try:
            return json.dumps(dataclasses.asdict(obj), default=_default, indent=2)
        except Exception:
            return "{}"


# ── Service factory ────────────────────────────────────────────

def create_analyst_service(config: ProviderConfig) -> AIAnalystService:
    """
    Convenience factory used by the DI container and tests.
    """
    return AIAnalystService(
        provider=       get_provider(config),
        prompt_builder= PromptBuilder(),
        output_parser=  OutputParser(),
    )
