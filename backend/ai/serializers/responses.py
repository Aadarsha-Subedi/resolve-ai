from dataclasses import dataclass

from django.conf import settings

from ai.models import AIUsageLog
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


@dataclass(frozen=True)
class UsageLogData(BaseResponseData):
    log: AIUsageLog

    def to_dict(self) -> dict:
        row = self.log
        return {
            "id": str(row.id),
            "feature": row.feature,
            "outcome": row.outcome,
            "user": (
                {
                    "id": str(row.user_id),
                    "name": row.user.display_name or row.user.email,
                }
                if row.user_id
                else None
            ),
            "provider": row.provider,
            "model": row.model,
            "question": row.question,
            "answer": row.answer,
            "details": row.details,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "error_code": row.error_code,
            "created_at": row.created_at.isoformat(),
        }
