"""
Anthropic Claude provider.

Uses the official anthropic SDK (async client).
Implements json_mode by appending JSON instruction to system prompt
since Claude doesn't have a native JSON mode flag (unlike OpenAI).
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import structlog

from app.domain.models.analysis import LLMProvider, LLMResponse, ProviderConfig
from app.infrastructure.ai.provider_protocol import (
    LLMContextLengthError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)

logger = structlog.get_logger(__name__)


class AnthropicProvider:
    """Anthropic Claude implementation of LLMProviderProtocol."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client: object | None = None

    def _get_client(self) -> object:
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(
                api_key=self._config.api_key,
                timeout=float(self._config.timeout_s),
            )
        return self._client

    async def complete(
        self,
        system_prompt: str,
        user_prompt:   str,
        *,
        temperature:   float | None = None,
        max_tokens:    int   | None = None,
        json_mode:     bool         = False,
    ) -> LLMResponse:
        import anthropic

        sys_prompt = system_prompt
        if json_mode:
            sys_prompt += (
                "\n\nYou MUST respond with valid JSON only. "
                "No markdown fences, no preamble, no explanation outside the JSON object."
            )

        temp    = temperature if temperature is not None else self._config.temperature
        max_tok = max_tokens  if max_tokens  is not None else self._config.max_tokens

        logger.debug(
            "anthropic_request",
            model=self._config.model,
            temperature=temp,
            max_tokens=max_tok,
        )

        try:
            client = self._get_client()
            response = await client.messages.create(  # type: ignore[union-attr]
                model=self._config.model,
                max_tokens=max_tok,
                temperature=temp,
                system=sys_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.RateLimitError as exc:
            raise LLMRateLimitError("anthropic") from exc
        except anthropic.BadRequestError as exc:
            if "context" in str(exc).lower() or "length" in str(exc).lower():
                raise LLMContextLengthError("anthropic", str(exc)) from exc
            raise LLMProviderError("anthropic", str(exc)) from exc
        except anthropic.APIStatusError as exc:
            raise LLMProviderError("anthropic", str(exc), exc.status_code) from exc
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError("anthropic", f"Timed out after {self._config.timeout_s}s") from exc

        content = response.content[0].text if response.content else ""
        return LLMResponse(
            content=           content,
            prompt_tokens=     response.usage.input_tokens,
            completion_tokens= response.usage.output_tokens,
            model=             response.model,
            finish_reason=     response.stop_reason or "stop",
        )

    async def stream(
        self,
        system_prompt: str,
        user_prompt:   str,
        *,
        temperature: float | None = None,
        max_tokens:  int   | None = None,
    ) -> AsyncGenerator[str, None]:
        import anthropic

        temp    = temperature if temperature is not None else self._config.temperature
        max_tok = max_tokens  if max_tokens  is not None else self._config.max_tokens

        try:
            client = self._get_client()
            async with client.messages.stream(  # type: ignore[union-attr]
                model=self._config.model,
                max_tokens=max_tok,
                temperature=temp,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.RateLimitError as exc:
            raise LLMRateLimitError("anthropic") from exc
        except anthropic.APIStatusError as exc:
            raise LLMProviderError("anthropic", str(exc), exc.status_code) from exc

    @property
    def provider_name(self) -> LLMProvider:
        return LLMProvider.ANTHROPIC

    @property
    def model_name(self) -> str:
        return self._config.model
