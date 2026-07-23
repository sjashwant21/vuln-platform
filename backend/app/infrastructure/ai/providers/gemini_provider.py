"""
Google Gemini provider (gemini-1.5-pro, gemini-1.5-flash).

Uses google-generativeai SDK. Gemini has native JSON mode via
response_mime_type="application/json" in generation config.

Safety settings are set to BLOCK_NONE for security content —
default Gemini safety filters block legitimate security analysis
content like CVE descriptions and exploit discussion.
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

# Disable safety filters for security content — these block legitimate analysis
_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH",        "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",  "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT",  "threshold": "BLOCK_NONE"},
]


class GeminiProvider:
    """Google Gemini implementation of LLMProviderProtocol."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._model: object | None = None

    def _get_model(self, json_mode: bool = False) -> object:
        import google.generativeai as genai

        genai.configure(api_key=self._config.api_key)

        gen_config_kwargs: dict = {
            "temperature":     self._config.temperature,
            "max_output_tokens": self._config.max_tokens,
        }
        if json_mode:
            gen_config_kwargs["response_mime_type"] = "application/json"

        return genai.GenerativeModel(
            model_name=self._config.model,
            generation_config=genai.types.GenerationConfig(**gen_config_kwargs),
            safety_settings=_SAFETY_SETTINGS,
            system_instruction=None,   # injected per-call
        )

    async def complete(
        self,
        system_prompt: str,
        user_prompt:   str,
        *,
        temperature:   float | None = None,
        max_tokens:    int   | None = None,
        json_mode:     bool         = False,
    ) -> LLMResponse:
        # Gemini doesn't have a separate system prompt field in all SDK versions;
        # prepend it to the user message with a clear separator.
        full_prompt = (
            f"<system_instructions>\n{system_prompt}\n</system_instructions>\n\n"
            f"{user_prompt}"
        )

        logger.debug("gemini_request", model=self._config.model, json_mode=json_mode)

        try:
            model = self._get_model(json_mode=json_mode)

            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: model.generate_content(full_prompt),  # type: ignore[union-attr]
                ),
                timeout=float(self._config.timeout_s),
            )
        except TimeoutError as exc:
            raise LLMTimeoutError("gemini", f"Timed out after {self._config.timeout_s}s") from exc
        except Exception as exc:
            err = str(exc).lower()
            if "quota" in err or "rate" in err:
                raise LLMRateLimitError("gemini") from exc
            if "context" in err or "token" in err and "limit" in err:
                raise LLMContextLengthError("gemini", str(exc)) from exc
            raise LLMProviderError("gemini", str(exc)) from exc

        content = response.text if hasattr(response, "text") else ""
        usage   = getattr(response, "usage_metadata", None)

        return LLMResponse(
            content=           content,
            prompt_tokens=     getattr(usage, "prompt_token_count",     0) if usage else 0,
            completion_tokens= getattr(usage, "candidates_token_count", 0) if usage else 0,
            model=             self._config.model,
            finish_reason=     "stop",
        )

    async def stream(
        self,
        system_prompt: str,
        user_prompt:   str,
        *,
        temperature: float | None = None,
        max_tokens:  int   | None = None,
    ) -> AsyncGenerator[str, None]:
        full_prompt = (
            f"<system_instructions>\n{system_prompt}\n</system_instructions>\n\n"
            f"{user_prompt}"
        )

        try:
            model = self._get_model()
            response = model.generate_content(full_prompt, stream=True)  # type: ignore[union-attr]
            for chunk in response:
                if hasattr(chunk, "text") and chunk.text:
                    yield chunk.text
        except Exception as exc:
            raise LLMProviderError("gemini", str(exc)) from exc

    @property
    def provider_name(self) -> LLMProvider:
        return LLMProvider.GEMINI

    @property
    def model_name(self) -> str:
        return self._config.model
