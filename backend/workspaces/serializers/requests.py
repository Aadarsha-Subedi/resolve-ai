from rest_framework import serializers

from common.serializers.base import StrictSerializer
from common.serializers.fields import NormalizedEmailField
from workspaces.constants import messages
from workspaces.constants.settings import (
    INVITATION_MAX_PER_REQUEST,
    JOIN_LINK_DEFAULT_EXPIRY,
    JOIN_LINK_EXPIRY_CHOICES,
    LOGO_CONTENT_TYPES,
    LOGO_MAX_BYTES,
    NAME_MAX_LENGTH,
    SLUG_PATTERN,
)


class CreateWorkspaceSerializer(StrictSerializer):
    name = serializers.CharField(max_length=NAME_MAX_LENGTH, trim_whitespace=True)
    slug = serializers.CharField(required=False, trim_whitespace=True)

    def validate_slug(self, value: str) -> str:
        value = value.lower()
        if not SLUG_PATTERN.match(value):
            raise serializers.ValidationError(
                "Use 3-40 lowercase letters, digits or hyphens, starting and ending with a letter or digit."
            )
        return value


class UpdateWorkspaceSerializer(StrictSerializer):
    # No slug field: the address is immutable and unknown fields are rejected.
    name = serializers.CharField(
        required=False, max_length=NAME_MAX_LENGTH, trim_whitespace=True
    )
    portal_enabled = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(messages.MESSAGE_NOTHING_TO_UPDATE)
        return attrs


class TransferOwnershipSerializer(StrictSerializer):
    user_id = serializers.UUIDField()


class RotateJoinLinkSerializer(StrictSerializer):
    expires_in = serializers.ChoiceField(
        choices=list(JOIN_LINK_EXPIRY_CHOICES), default=JOIN_LINK_DEFAULT_EXPIRY
    )


class RedeemJoinLinkSerializer(StrictSerializer):
    token = serializers.CharField(max_length=200, trim_whitespace=True)


class CreateInvitationsSerializer(StrictSerializer):
    emails = serializers.ListField(
        child=NormalizedEmailField(),
        min_length=1,
        max_length=INVITATION_MAX_PER_REQUEST,
        allow_empty=False,
    )


class LogoUploadUrlSerializer(StrictSerializer):
    content_type = serializers.ChoiceField(choices=list(LOGO_CONTENT_TYPES))
    size = serializers.IntegerField(min_value=1, max_value=LOGO_MAX_BYTES)


class ConfirmLogoSerializer(StrictSerializer):
    key = serializers.CharField(max_length=300)
