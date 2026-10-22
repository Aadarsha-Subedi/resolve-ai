"""Builds the provider a call should use. This is the only place that knows the vendors."""

from django.conf import settings

from common.llm.base import LLMProvider, LLMUnavailableError
from common.llm.constants import (
    ALLOWED_MODELS,
    DEFAULT_MODELS,
    PROVIDER_GEMINI,
    PROVIDER_OPENAI,
    RESOLVE_AI_MODELS,
)
from common.llm.gemini import GeminiProvider
from common.llm.openai_provider import OpenAIProvider

_PROVIDER_CLASSES = {
    PROVIDER_GEMINI: GeminiProvider,
    PROVIDER_OPENAI: OpenAIProvider,
}


def create_provider(
    provider: str, api_key: str, model: str | None = None
) -> LLMProvider:
    """A provider for the user's own key. Unknown providers and models are refused."""
    if provider not in _PROVIDER_CLASSES:
        raise ValueError(f"Unknown LLM provider: {provider}")
    model = model or DEFAULT_MODELS[provider]
    if model not in ALLOWED_MODELS[provider]:
        raise ValueError(f"Model not allowed for {provider}: {model}")
    return _PROVIDER_CLASSES[provider](api_key=api_key, model=model)


def resolve_ai_provider(model: str | None = None) -> LLMProvider:
    """A provider on the Resolve AI Gemini key, limited to the cheap models."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise LLMUnavailableError()
    model = model or DEFAULT_MODELS[PROVIDER_GEMINI]
    if model not in RESOLVE_AI_MODELS:
        raise ValueError(f"Model not allowed on the Resolve AI key: {model}")
    return GeminiProvider(api_key=api_key, model=model)
