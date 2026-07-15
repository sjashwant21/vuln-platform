"""
Local LLM provider — Ollama / llama.cpp / vLLM / any OpenAI-compatible server.

Uses the OpenAI SDK pointed at a local base_url.
This covers:
  - Ollama:     base_url="http://localhost:11434/v1", api_key="ollama"
  - llama.cpp:  base_url="http://localhost:8080/v1",  api_key="none"
  - vLLM:       base_url="http://localhost:8000/v1",  api_key="EMPTY"
  - LM Studio:  base_url="http://localhost:1234/v1",  api_key="lm-studio"

json_mode is attempted but silently degraded if the local model
doesn't support response_format (most don't). Instead we add explicit
JSON instruction to the system prompt as fallback.

Performance note: local models are typically much slower. The timeout
should be set generously (300s+) in ProviderConfig for large models.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import structlog

from app.domain.models.analysis import LLMProvider, LLMResponse, ProviderConfig
from app.infrastructure.ai.provider_protocol import (
    LLMProviderError,
    LLMTimeoutError,
)

logger = structlog.get_logger(__name__)


class LocalLLMProvider:
    """
    OpenAI-compatible local LLM implementation of LLMProviderProtocol.

    Falls back gracefully when the server doesn't support all OpenAI features.
    """

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client: object | None = None

    def _get_client(self) -> object:
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=  self._config.api_key or "none",
                base_url= self._config.base_url or "http://localhost:11434/v1",
                timeout=  float(self._config.timeout_s),
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
        import openai

        temp    = temperature if temperature is not None else self._config.temperature
        max_tok = max_tokens  if max_tokens  is not None else self._config.max_tokens

        sys_prompt = system_prompt
        if json_mode:
            sys_prompt += (
                "\n\nIMPORTANT: Your entire response must be a single valid JSON object. "
                "No markdown, no explanation, no text outside the JSON."
            )

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": user_prompt},
        ]

        kwargs: dict = {
            "model":       self._config.model,
            "temperature": temp,
            "messages":    messages,
        }
        if max_tok:
            kwargs["max_tokens"] = max_tok

        logger.debug(
            "local_llm_request",
            model=self._config.model,
            base_url=self._config.base_url,
        )

        try:
            client   = self._get_client()
            response = await client.chat.completions.create(**kwargs)  # type: ignore[union-attr]
        except openai.APIConnectionError as exc:
            raise LLMProviderError(
                "local",
                f"Cannot connect to local LLM at {self._config.base_url}. "
                f"Is Ollama/llama.cpp running? Error: {exc}",
            ) from exc
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError(
                "local",
                f"Local LLM timed out after {self._config.timeout_s}s. "
                "Consider increasing timeout_s for large models.",
            ) from exc
        except openai.APIStatusError as exc:
            raise LLMProviderError("local", str(exc), exc.status_code) from exc

        choice  = response.choices[0]
        content = choice.message.content or ""
        usage   = response.usage

        return LLMResponse(
            content=           content,
            prompt_tokens=     usage.prompt_tokens     if usage else 0,
            completion_tokens= usage.completion_tokens if usage else 0,
            model=             response.model or self._config.model,
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
            stream = await client.chat.completions.create(  # type: ignore[union-attr]
                model=self._config.model,
                temperature=temp,
                max_tokens=max_tok,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except openai.APIConnectionError as exc:
            raise LLMProviderError(
                "local",
                f"Cannot connect to local LLM at {self._config.base_url}",
            ) from exc
        except openai.APIStatusError as exc:
            raise LLMProviderError("local", str(exc), exc.status_code) from exc

    @property
    def provider_name(self) -> LLMProvider:
        return LLMProvider.LOCAL

    @property
    def model_name(self) -> str:
        return self._config.model
