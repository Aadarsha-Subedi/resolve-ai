from rest_framework import serializers

from audit.constants.actions import ACTIONS
from audit.constants.settings import ACTION_MAX_LENGTH


class AuditFilterSerializer(serializers.Serializer):
    """Query-string filters; unknown parameters (limit, offset) are ignored."""

    action = serializers.ChoiceField(required=False, choices=sorted(ACTIONS))
    action_prefix = serializers.CharField(required=False, max_length=ACTION_MAX_LENGTH)
    actor = serializers.UUIDField(required=False)
    target_type = serializers.CharField(required=False, max_length=30)
    target_id = serializers.CharField(required=False, max_length=64)
    created_from = serializers.DateField(required=False)
    created_to = serializers.DateField(required=False)
