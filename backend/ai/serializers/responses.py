from dataclasses import dataclass

from django.conf import settings

from ai.services import allowance
from ai.services.settings_service import SettingsView
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
    view: SettingsView

    def to_dict(self) -> dict:
        r = self.view.row
        usage = allowance.usage(r.workspace_id, r.user_id)
        return {
            "mode": r.mode,
            "resolve_ai_model": r.resolve_ai_model,
            "active_provider": r.active_provider or None,
            "keys": [
                {
                    "provider": k.provider,
                    "model": k.model,
                    "last4": k.key_last4,
                    "checked_at": k.checked_at.isoformat(),
                }
                for k in self.view.keys
            ],
            "usage": {
                "used_today": usage.used,
                "limit": usage.limit,
                "remaining": usage.remaining,
                "resets_at": usage.resets_at.isoformat(),
            },
            "options": _options(),
        }
