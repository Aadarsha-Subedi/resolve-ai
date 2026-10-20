from rest_framework import serializers

from common.serializers.base import StrictSerializer


class AttachReviewSerializer(StrictSerializer):
    workspace_id = serializers.UUIDField()
    ticket_id = serializers.UUIDField()
