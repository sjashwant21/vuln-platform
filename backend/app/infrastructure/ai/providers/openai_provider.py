"""
OpenAI provider (GPT-4o, GPT-4-turbo, etc.).

Uses json_mode=True via response_format parameter when requested —
this is the most reliable way to get valid JSON from OpenAI models.
Also works with any OpenAI-compatible endpoint (Together AI, Groq, etc.)
by setting config.base_url.
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


class OpenAIProvider:
    """OpenAI / OpenAI-compatible implementation of LLMProviderProtocol."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client: object | None = None

    def _get_client(self) -> object:
        if self._client is None:
            import openai
            kwargs: dict = {
                "api_key": self._config.api_key,
                "timeout": float(self._config.timeout_s),
            }
            if self._config.base_url:
                kwargs["base_url"] = self._config.base_url
            self._client = openai.AsyncOpenAI(**kwargs)
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
        import openai

        temp    = temperature if temperature is not None else self._config.temperature
        max_tok = max_tokens  if max_tokens  is not None else self._config.max_tokens

        kwargs: dict = {
            "model":       self._config.model,
            "temperature": temp,
            "max_tokens":  max_tok,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        logger.debug("openai_request", model=self._config.model, json_mode=json_mode)

        try:
            client   = self._get_client()
            response = await client.chat.completions.create(**kwargs)  # type: ignore[union-attr]
        except openai.RateLimitError as exc:
            retry = int(exc.response.headers.get("retry-after", 60)) if hasattr(exc, "response") else None
            raise LLMRateLimitError("openai", retry) from exc
        except openai.BadRequestError as exc:
            if "context_length" in str(exc) or "maximum context" in str(exc):
                raise LLMContextLengthError("openai", str(exc)) from exc
            raise LLMProviderError("openai", str(exc)) from exc
        except openai.APIStatusError as exc:
            raise LLMProviderError("openai", str(exc), exc.status_code) from exc
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError("openai", f"Timed out after {self._config.timeout_s}s") from exc

        choice  = response.choices[0]
        content = choice.message.content or ""
        usage   = response.usage

        return LLMResponse(
            content=           content,
            prompt_tokens=     usage.prompt_tokens     if usage else 0,
            completion_tokens= usage.completion_tokens if usage else 0,
            model=             response.model,
            finish_reason=     choice.finish_reason or "stop",
        )

    async def stream(
        self,
        system_prompt: str,
        user_prompt:   str,
        *,
        temperature: float | None = None,
        max_tokens:  int   | None = None,
    ) -> AsyncGenerator[str, None]:
        import openai

        temp    = temperature if temperature is not None else self._config.temperature
        max_tok = max_tokens  if max_tokens  is not None else self._config.max_tokens

        try:
            client = self._get_client()
            async with await client.chat.completions.create(  # type: ignore[union-attr]
                model=self._config.model,
                temperature=temp,
                max_tokens=max_tok,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                stream=True,
            ) as stream:
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        yield delta
        except openai.RateLimitError as exc:
            raise LLMRateLimitError("openai") from exc
        except openai.APIStatusError as exc:
            raise LLMProviderError("openai", str(exc), exc.status_code) from exc

    @property
    def provider_name(self) -> LLMProvider:
        return LLMProvider.OPENAI

    @property
    def model_name(self) -> str:
        return self._config.model
