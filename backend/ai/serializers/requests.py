from rest_framework import serializers

from ai.constants import messages
from ai.constants.settings import (
    API_KEY_MAX_LENGTH,
    API_KEY_MIN_LENGTH,
    MODE_OWN_KEY,
    MODE_RESOLVE_AI,
    MODEL_MAX_LENGTH,
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
    own_provider = serializers.ChoiceField(choices=list(PROVIDERS), required=False)
    own_model = serializers.CharField(max_length=MODEL_MAX_LENGTH, required=False)
    api_key = serializers.CharField(
        min_length=API_KEY_MIN_LENGTH,
        max_length=API_KEY_MAX_LENGTH,
        trim_whitespace=True,
        validators=[_no_spaces],
        write_only=True,
        required=False,
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(messages.MESSAGE_NOTHING_TO_UPDATE)
        return attrs
