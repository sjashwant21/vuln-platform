"""
LLM provider abstraction via Python Protocol (structural subtyping).

Why Protocol over ABC:
  - No inheritance required — any class with the right methods satisfies it
  - Third-party wrappers need zero modification to existing code
  - Runtime checkable via isinstance() when needed
  - Enables MyPy structural checking without coupling

Every provider must implement exactly two methods:
  complete()    — single prompt → response (used for structured stage outputs)
  stream()      — async generator for streaming (used for long reports)

The factory function get_provider() is the single injection point —
callers never instantiate providers directly.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Protocol, runtime_checkable

from app.domain.models.analysis import LLMProvider, LLMResponse, ProviderConfig


@runtime_checkable
class LLMProviderProtocol(Protocol):
    """
    Structural interface that every LLM provider must satisfy.

    Providers are stateless — all configuration lives in ProviderConfig
    passed at construction time. This makes them safe to share across
    concurrent requests.
    """

    async def complete(
        self,
        system_prompt: str,
        user_prompt:   str,
        *,
        temperature:   float | None = None,
        max_tokens:    int   | None = None,
        json_mode:     bool         = False,
    ) -> LLMResponse:
        """
        Send a single completion request and return the full response.

        Args:
            system_prompt: The analyst persona and task instructions
            user_prompt:   The structured vulnerability data
            temperature:   Override config temperature (0.0 = deterministic)
            max_tokens:    Override config max_tokens
            json_mode:     Hint to provider to return valid JSON (if supported)

        Returns:
            LLMResponse with content, token counts, and finish reason

        Raises:
            LLMProviderError: on any provider-side failure
            LLMTimeoutError:  if the request exceeds timeout_s
            LLMRateLimitError: if the provider rate-limits us
        """
        ...

    async def stream(
        self,
        system_prompt: str,
        user_prompt:   str,
        *,
        temperature: float | None = None,
        max_tokens:  int   | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens as they are generated.
        Used for long-form report generation where UX matters.

        Yields:
            str chunks as they arrive from the provider
        """
        ...

    @property
    def provider_name(self) -> LLMProvider:
        """Which provider this instance represents."""
        ...

    @property
    def model_name(self) -> str:
        """The specific model being used."""
        ...


# ── Provider errors ────────────────────────────────────────────

class LLMProviderError(Exception):
    """Base for all LLM provider errors."""
    def __init__(self, provider: str, message: str, status_code: int | None = None) -> None:
        super().__init__(f"[{provider}] {message}")
        self.provider    = provider
        self.status_code = status_code


class LLMTimeoutError(LLMProviderError):
    """Request exceeded the configured timeout."""


class LLMRateLimitError(LLMProviderError):
    """Provider returned a rate limit response."""
    def __init__(self, provider: str, retry_after_s: int | None = None) -> None:
        super().__init__(provider, f"Rate limited. Retry after {retry_after_s}s")
        self.retry_after_s = retry_after_s


class LLMContextLengthError(LLMProviderError):
    """Prompt exceeded the model's context window."""


class LLMOutputParseError(Exception):
    """Provider returned output that failed structured parsing."""
    def __init__(self, stage: str, raw_output: str, reason: str) -> None:
        super().__init__(f"Failed to parse {stage} output: {reason}")
        self.stage      = stage
        self.raw_output = raw_output
        self.reason     = reason


# ── Provider factory ───────────────────────────────────────────

def get_provider(config: ProviderConfig) -> LLMProviderProtocol:
    """
    Factory function — the only place provider classes are instantiated.

    This is the single injection point for the entire AI pipeline.
    Swap providers by changing ProviderConfig; nothing else changes.
    """
    from app.domain.models.analysis import LLMProvider

    if config.provider == LLMProvider.ANTHROPIC:
        from app.infrastructure.ai.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(config)

    if config.provider == LLMProvider.OPENAI:
        from app.infrastructure.ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(config)

    if config.provider == LLMProvider.GROQ:
        from app.infrastructure.ai.providers.groq_provider import GroqProvider
        return GroqProvider(config)

    if config.provider == LLMProvider.GEMINI:
        from app.infrastructure.ai.providers.gemini_provider import GeminiProvider
        return GeminiProvider(config)

    if config.provider == LLMProvider.LOCAL:
        from app.infrastructure.ai.providers.local_provider import LocalLLMProvider
        return LocalLLMProvider(config)

    raise ValueError(f"Unknown provider: {config.provider}")
