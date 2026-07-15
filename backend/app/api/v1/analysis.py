"""
AI Security Analyst API router — /v1/analysis/*

Endpoints:
  POST /v1/analysis/analyse          Full five-stage analysis
  POST /v1/analysis/analyse/stream   Stream the management summary
  GET  /v1/analysis/providers        List available/configured providers

All routes require authentication.
Analysis is expensive (5 LLM calls) — rate limited to 5/hour per org.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.schemas.analysis_schemas import (
    AnalyseRequest,
    SecurityAnalysisResponse,
    analysis_to_response,
)
from app.dependencies import CurrentUser

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/analysis", tags=["AI Security Analyst"])


def _build_service(body: AnalyseRequest) -> object:
    """Build the analyst service from request parameters."""
    from app.config import get_settings
    from app.application.services.ai_analyst_service import create_analyst_service
    from app.domain.models.analysis import LLMProvider, ProviderConfig

    cfg = get_settings()

    provider_map = {
        "groq":      LLMProvider.GROQ,
        "anthropic": LLMProvider.ANTHROPIC,
        "openai":    LLMProvider.OPENAI,
        "gemini":    LLMProvider.GEMINI,
        "local":     LLMProvider.LOCAL,
    }
    provider = provider_map.get(body.provider, LLMProvider.GROQ)  # default: Groq

    # Default models per provider
    default_models = {
        LLMProvider.GROQ:      cfg.groq_model,
        LLMProvider.ANTHROPIC: getattr(cfg, "anthropic_model", "claude-3-5-sonnet-20241022"),
        LLMProvider.OPENAI:    "gpt-4o",
        LLMProvider.GEMINI:    "gemini-1.5-pro",
        LLMProvider.LOCAL:     "llama3.2",
    }

    # API keys per provider
    api_keys = {
        LLMProvider.GROQ:      cfg.groq_api_key,
        LLMProvider.ANTHROPIC: getattr(cfg, "anthropic_api_key", None),
        LLMProvider.OPENAI:    getattr(cfg, "openai_api_key", None),
        LLMProvider.GEMINI:    getattr(cfg, "gemini_api_key", None),
        LLMProvider.LOCAL:     "none",
    }

    model = body.model or default_models[provider]
    api_key = api_keys.get(provider)

    if provider != LLMProvider.LOCAL and not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"API key for provider '{body.provider}' is not configured",
        )

    pc = ProviderConfig(
        provider=    provider,
        model=       model,
        api_key=     api_key,
        base_url=    getattr(cfg, "local_llm_base_url", None)
                     if provider == LLMProvider.LOCAL else None,
        timeout_s=   120,
        temperature= 0.1,
        max_tokens=  4096,
    )
    return create_analyst_service(pc)


def _build_request(body: AnalyseRequest) -> object:
    """Convert API schema to domain AnalysisRequest."""
    from app.domain.models.analysis import (
        AnalysisRequest, ServiceInput, VulnerabilityInput,
    )

    services = tuple(
        ServiceInput(
            port=     s.port,
            protocol= s.protocol,
            service=  s.service,
            version=  s.version,
            banner=   s.banner,
        )
        for s in body.services
    )

    vulnerabilities = tuple(
        VulnerabilityInput(
            cve_id=             v.cve_id,
            title=              v.title,
            severity=           v.severity,
            cvss_score=         v.cvss_score,
            cvss_vector=        v.cvss_vector,
            description=        v.description,
            service=            v.service,
            port=               v.port,
            affected_version=   v.affected_version,
            has_public_exploit= v.has_public_exploit,
            has_patch=          v.has_patch,
            references=         tuple(v.references),
        )
        for v in body.vulnerabilities
    )

    return AnalysisRequest(
        asset_id=           body.asset_id,
        asset_hostname=     body.asset_hostname,
        asset_ip=           body.asset_ip,
        asset_os=           body.asset_os,
        asset_criticality=  body.asset_criticality,
        internet_exposed=   body.internet_exposed,
        services=           services,
        vulnerabilities=    vulnerabilities,
        org_name=           body.org_name,
        scan_date=          body.scan_date or datetime.now(UTC),
        additional_context= body.additional_context,
    )


# ── POST /analysis/analyse ─────────────────────────────────────

@router.post(
    "/analyse",
    response_model=SecurityAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Run full AI security analysis",
    description="""
Runs a five-stage AI security analysis pipeline:
1. **Executive Summary** — Business-level risk overview
2. **Technical Analysis** — Deep technical findings for engineers
3. **Risk Prioritization** — Ranked by actual business risk, not CVSS
4. **Remediation Recommendations** — Step-by-step fix instructions
5. **Management Summary** — One-page board-ready report

This endpoint makes 5 LLM API calls and typically takes 30-90 seconds.
Rate limited to **5 analyses per hour per organization**.

Supported providers: `anthropic` (default), `openai`, `gemini`, `local`
    """,
)
async def analyse(
    body:         AnalyseRequest,
    current_user: CurrentUser,
) -> SecurityAnalysisResponse:
    from app.infrastructure.ai.provider_protocol import (
        LLMProviderError, LLMRateLimitError, LLMTimeoutError,
    )

    svc     = _build_service(body)
    request = _build_request(body)

    logger.info(
        "analysis_api_request",
        org_id=     current_user.org_id,
        user_id=    current_user.user_id,
        asset_id=   body.asset_id,
        provider=   body.provider,
        vuln_count= len(body.vulnerabilities),
    )

    try:
        analysis = await svc.analyse(request)  # type: ignore[union-attr]
    except LLMRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"LLM provider rate limit reached: {exc}",
        ) from exc
    except LLMTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"LLM provider timed out: {exc}",
        ) from exc
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider error: {exc}",
        ) from exc

    return analysis_to_response(analysis)


# ── POST /analysis/analyse/stream ──────────────────────────────

@router.post(
    "/analyse/stream",
    summary="Stream the management summary as it generates",
    description="""
Streams the management summary section in real-time as tokens arrive.
Useful for displaying progressive output in the UI.

Returns a text/event-stream response.
Full structured analysis must be fetched separately via POST /analyse.
    """,
)
async def analyse_stream(
    body:         AnalyseRequest,
    current_user: CurrentUser,
) -> StreamingResponse:
    from app.domain.models.analysis import AnalysisStage
    from app.infrastructure.ai.provider_protocol import LLMProviderError

    svc     = _build_service(body)
    request = _build_request(body)

    async def _event_stream():
        try:
            async for chunk in svc.analyse_stream(  # type: ignore[union-attr]
                request, stage=AnalysisStage.EXECUTIVE
            ):
                yield f"data: {chunk}\n\n"
        except LLMProviderError as exc:
            yield f"data: [ERROR] {exc}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── GET /analysis/providers ────────────────────────────────────

@router.get(
    "/providers",
    summary="List configured LLM providers",
)
async def list_providers(current_user: CurrentUser) -> dict:
    from app.config import get_settings
    cfg = get_settings()

    configured = []

    if getattr(cfg, "groq_api_key", None):
        configured.append({
            "id":      "groq",
            "name":    "Groq (LLaMA 3 70B) — Free",
            "models":  ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"],
            "default": True,
        })
    if getattr(cfg, "anthropic_api_key", None):
        configured.append({
            "id":      "anthropic",
            "name":    "Anthropic Claude",
            "models":  ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
        })
    if getattr(cfg, "openai_api_key", None):
        configured.append({
            "id":     "openai",
            "name":   "OpenAI",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        })
    if getattr(cfg, "gemini_api_key", None):
        configured.append({
            "id":     "gemini",
            "name":   "Google Gemini",
            "models": ["gemini-1.5-pro", "gemini-1.5-flash"],
        })

    # Local is always available (may fail at runtime if Ollama not running)
    configured.append({
        "id":      "local",
        "name":    "Local LLM (Ollama / llama.cpp)",
        "models":  ["llama3.2", "mistral", "codellama", "phi3"],
        "base_url": getattr(cfg, "local_llm_base_url", "http://localhost:11434/v1"),
    })

    return {"providers": configured}
