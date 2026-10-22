from dataclasses import dataclass

from django.conf import settings

from ai.models import UserWorkspaceLLMSettings
from ai.services import allowance
from common.llm.constants import (
    ALLOWED_MODELS,
    DEFAULT_MODELS,
    PROVIDERS,
    RESOLVE_AI_MODELS,
)
from common.response.domain import BaseResponseData


def _options() -> dict:
    return {
        "resolve_ai": {
            "available": bool(settings.GEMINI_API_KEY),
            "models": list(RESOLVE_AI_MODELS),
        },
        "providers": {
            name: {
                "models": list(ALLOWED_MODELS[name]),
                "default": DEFAULT_MODELS[name],
            }
            for name in PROVIDERS
        },
    }


@dataclass(frozen=True)
class LLMSettingsData(BaseResponseData):
    row: UserWorkspaceLLMSettings

    def to_dict(self) -> dict:
        r = self.row
        usage = allowance.usage(r.workspace_id, r.user_id)
        return {
            "mode": r.mode,
            "resolve_ai_model": r.resolve_ai_model,
            "own_key": {
                "has_key": r.has_key,
                "provider": r.own_provider or None,
                "model": r.own_model or None,
                "last4": r.own_key_last4 or None,
                "checked_at": r.own_key_checked_at.isoformat()
                if r.own_key_checked_at
                else None,
            },
            "usage": {
                "used_today": usage.used,
                "limit": usage.limit,
                "remaining": usage.remaining,
                "resets_at": usage.resets_at.isoformat(),
            },
            "options": _options(),
        }
