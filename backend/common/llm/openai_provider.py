"""OpenAI through the official openai SDK."""

import openai

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
from common.llm.constants import PROVIDER_OPENAI, REQUEST_TIMEOUT_SECONDS


def _map_error(exc: Exception) -> LLMError:
    if isinstance(exc, openai.APITimeoutError):
        return LLMTimeoutError()
    if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return LLMInvalidKeyError()
    if isinstance(exc, openai.RateLimitError):
        # Also raised when the account has run out of credit (insufficient_quota).
        return LLMRateLimitedError()
    return LLMUnavailableError()


class OpenAIProvider(LLMProvider):
    provider = PROVIDER_OPENAI

    def __init__(self, api_key: str, model: str):
        self.model = model
        self._client = openai.OpenAI(
            api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=0
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})
        options = {}
        if request.json_output:
            options["response_format"] = {"type": "json_object"}
        try:
            # No temperature: reasoning models reject anything but the default.
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=request.max_output_tokens,
                **options,
            )
        except Exception as exc:  # noqa: BLE001 - any SDK failure maps to an LLMError
            raise _map_error(exc) from None
        choice = response.choices[0] if response.choices else None
        text = choice.message.content if choice else None
        if not text or not text.strip():
            raise LLMBadResponseError()
        usage = response.usage
        return LLMResponse(
            text=text,
            model=self.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    def validate_key(self) -> None:
        try:
            self._client.models.retrieve(self.model)
        except Exception as exc:  # noqa: BLE001 - any SDK failure maps to an LLMError
            raise _map_error(exc) from None
