"""Gemini through the official google-genai SDK."""

import httpx
from google import genai
from google.genai import errors, types

from common.llm.base import (
    LLMBadResponseError,
    LLMError,
    LLMInvalidKeyError,
    LLMProvider,
    LLMRateLimitedError,
    LLMRequest,
    LLMResponse,
    LLMTimeoutError,
    LLMUnavailableError,
)
from common.llm.constants import PROVIDER_GEMINI, REQUEST_TIMEOUT_SECONDS


def _map_error(exc: Exception) -> LLMError:
    if isinstance(exc, httpx.TimeoutException):
        return LLMTimeoutError()
    if isinstance(exc, errors.APIError):
        status = exc.code
        text = (exc.message or "").lower()
        # An unknown key comes back as 400 INVALID_ARGUMENT, not 401.
        if status in (401, 403) or "api key" in text:
            return LLMInvalidKeyError()
        if status == 429:
            return LLMRateLimitedError()
        if status == 408 or status == 504:
            return LLMTimeoutError()
    return LLMUnavailableError()


class GeminiProvider(LLMProvider):
    provider = PROVIDER_GEMINI

    def __init__(self, api_key: str, model: str):
        self.model = model
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=REQUEST_TIMEOUT_SECONDS * 1000,  # milliseconds
                retry_options=types.HttpRetryOptions(attempts=1),  # no retries
            ),
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        config = types.GenerateContentConfig(
            system_instruction=request.system or None,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
            response_mime_type="application/json" if request.json_output else None,
        )
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=request.prompt, config=config
            )
            text = response.text
        except Exception as exc:  # noqa: BLE001 - any SDK failure maps to an LLMError
            raise _map_error(exc) from None
        if not text or not text.strip():
            raise LLMBadResponseError()
        usage = response.usage_metadata
        return LLMResponse(
            text=text,
            model=self.model,
            input_tokens=(usage.prompt_token_count or 0) if usage else 0,
            output_tokens=(usage.candidates_token_count or 0) if usage else 0,
        )

    def validate_key(self) -> None:
        try:
            self._client.models.get(model=self.model)
        except Exception as exc:  # noqa: BLE001 - any SDK failure maps to an LLMError
            raise _map_error(exc) from None
