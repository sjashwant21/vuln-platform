"""
Groq AI provider — drop-in replacement for Anthropic Claude.

Uses Groq's OpenAI-compatible API (https://api.groq.com/openai/v1).
Free tier: 30 requests/min, 14,400 requests/day.
Model: llama3-70b-8192 (comparable to GPT-4 for security analysis).

Groq's API is structurally identical to OpenAI's — this provider wraps
OpenAIProvider with Groq's base URL and maps LLMProvider.GROQ.
"""
from __future__ import annotations

import structlog

from app.domain.models.analysis import LLMProvider, ProviderConfig
from app.infrastructure.ai.providers.openai_provider import OpenAIProvider

logger = structlog.get_logger(__name__)

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider(OpenAIProvider):
    """
    Groq inference provider using LLaMA 3 70B (or other Groq-hosted models).

    Groq's API is 100% OpenAI-compatible, so this subclasses OpenAIProvider
    and simply overrides the base_url and provider_name. No other changes needed.
    """

    def __init__(self, config: ProviderConfig) -> None:
        # Inject Groq base URL into config
        groq_config = ProviderConfig(
            provider=    LLMProvider.GROQ,
            model=       config.model,
            api_key=     config.api_key,
            base_url=    _GROQ_BASE_URL,
            timeout_s=   config.timeout_s,
            temperature= config.temperature,
            max_tokens=  config.max_tokens,
        )
        super().__init__(groq_config)
        logger.info("groq_provider_init", model=config.model)

    @property
    def provider_name(self) -> LLMProvider:
        return LLMProvider.GROQ

    @property
    def model_name(self) -> str:
        return self._config.model
