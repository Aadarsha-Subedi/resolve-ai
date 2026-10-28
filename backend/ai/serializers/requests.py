from rest_framework import serializers

from ai.constants import messages
from ai.constants.settings import (
    API_KEY_MAX_LENGTH,
    API_KEY_MIN_LENGTH,
    MODE_OWN_KEY,
    MODE_RESOLVE_AI,
    MODEL_MAX_LENGTH,
    USAGE_FEATURES,
    USAGE_ORDERINGS,
    USAGE_OUTCOMES,
    USAGE_SEARCH_MAX_LENGTH,
)
from common.llm.constants import PROVIDERS
from common.serializers.base import StrictSerializer


def _no_spaces(value: str) -> str:
    if any(ch.isspace() for ch in value):
        raise serializers.ValidationError(messages.MESSAGE_KEY_FORMAT)
    return value


class UpdateSettingsSerializer(StrictSerializer):
    mode = serializers.ChoiceField(
        choices=[MODE_RESOLVE_AI, MODE_OWN_KEY], required=False
    )
    resolve_ai_model = serializers.CharField(
        max_length=MODEL_MAX_LENGTH, required=False
    )
    active_provider = serializers.ChoiceField(choices=list(PROVIDERS), required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(messages.MESSAGE_NOTHING_TO_UPDATE)
        return attrs


class SaveKeySerializer(StrictSerializer):
    """Add a key (`api_key` required the first time) or edit it (a new key, a new model)."""

    api_key = serializers.CharField(
        min_length=API_KEY_MIN_LENGTH,
        max_length=API_KEY_MAX_LENGTH,
        trim_whitespace=True,
        validators=[_no_spaces],
        write_only=True,
        required=False,
    )
    model = serializers.CharField(max_length=MODEL_MAX_LENGTH, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(messages.MESSAGE_NOTHING_TO_UPDATE)
        return attrs


class UsageFilterSerializer(serializers.Serializer):
    """Query-string filters of the usage log; limit and offset are read by the paginator."""

    search = serializers.CharField(
        required=False, max_length=USAGE_SEARCH_MAX_LENGTH, trim_whitespace=True
    )
    feature = serializers.ChoiceField(required=False, choices=list(USAGE_FEATURES))
    outcome = serializers.ChoiceField(required=False, choices=list(USAGE_OUTCOMES))
    actor = serializers.UUIDField(required=False)
    created_from = serializers.DateField(required=False)
    created_to = serializers.DateField(required=False)
    ordering = serializers.ChoiceField(
        required=False,
        default="-created_at",
        choices=[*USAGE_ORDERINGS, *(f"-{name}" for name in USAGE_ORDERINGS)],
    )
