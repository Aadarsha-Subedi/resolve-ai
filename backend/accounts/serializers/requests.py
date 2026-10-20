from rest_framework import serializers

from accounts.constants.settings import DISPLAY_NAME_MAX_LENGTH
from common.serializers.base import StrictSerializer


class UpdateProfileSerializer(StrictSerializer):
    display_name = serializers.CharField(
        max_length=DISPLAY_NAME_MAX_LENGTH, trim_whitespace=True, allow_blank=False
    )
