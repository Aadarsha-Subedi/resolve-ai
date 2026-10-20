from rest_framework import serializers

from common.serializers.base import StrictSerializer
from common.serializers.fields import NormalizedEmailField
from tickets.constants import messages
from tickets.constants.enums import (
    MessageVisibility,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from tickets.constants.settings import (
    CUSTOMER_NAME_MAX_LENGTH,
    DEFAULT_CATEGORY,
    DEFAULT_PRIORITY,
    PORTAL_HONEYPOT_FIELD,
    SUBJECT_MAX_LENGTH,
    TEXT_MAX_LENGTH,
)


def _subject(**kw):
    return serializers.CharField(
        max_length=SUBJECT_MAX_LENGTH, trim_whitespace=True, **kw
    )


def _text(**kw):
    return serializers.CharField(max_length=TEXT_MAX_LENGTH, trim_whitespace=True, **kw)


def _name(**kw):
    return serializers.CharField(
        max_length=CUSTOMER_NAME_MAX_LENGTH,
        trim_whitespace=True,
        allow_blank=True,
        **kw,
    )


class CreateTicketSerializer(StrictSerializer):
    subject = _subject()
    description = _text()
    customer_email = NormalizedEmailField()
    customer_name = _name(required=False)
    category = serializers.ChoiceField(
        choices=TicketCategory.choices, default=DEFAULT_CATEGORY
    )
    priority = serializers.ChoiceField(
        choices=TicketPriority.choices, default=DEFAULT_PRIORITY
    )


class UpdateTicketSerializer(StrictSerializer):
    """Status has its own endpoint, so it is not accepted here."""

    subject = _subject(required=False)
    description = _text(required=False)
    customer_email = NormalizedEmailField(required=False)
    customer_name = _name(required=False)
    category = serializers.ChoiceField(choices=TicketCategory.choices, required=False)
    priority = serializers.ChoiceField(choices=TicketPriority.choices, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(messages.MESSAGE_NOTHING_TO_UPDATE)
        return attrs


class ChangeStatusSerializer(StrictSerializer):
    status = serializers.ChoiceField(choices=TicketStatus.choices)


class AddMessageSerializer(StrictSerializer):
    body = _text()
    visibility = serializers.ChoiceField(choices=MessageVisibility.choices)


class TicketFilterSerializer(serializers.Serializer):
    """Query-string filters; unknown parameters (limit, offset) are ignored."""

    status = serializers.ChoiceField(required=False, choices=TicketStatus.choices)
    priority = serializers.ChoiceField(required=False, choices=TicketPriority.choices)
    category = serializers.ChoiceField(required=False, choices=TicketCategory.choices)
    created_from = serializers.DateField(required=False)
    created_to = serializers.DateField(required=False)
    q = serializers.CharField(required=False, max_length=100)
    waiting_for_reply = serializers.BooleanField(required=False)
    ordering = serializers.CharField(required=False, max_length=30)


class OverviewQuerySerializer(serializers.Serializer):
    """How much conversation and history to include (the newest items)."""

    messages_limit = serializers.IntegerField(
        required=False, min_value=1, max_value=100, default=50
    )
    events_limit = serializers.IntegerField(
        required=False, min_value=1, max_value=100, default=50
    )


class PortalTicketSerializer(serializers.Serializer):
    """Public form. The honeypot is read separately so a bot filling it is not told apart."""

    subject = _subject()
    description = _text()
    customer_email = NormalizedEmailField()
    customer_name = _name(required=False)
    category = serializers.ChoiceField(choices=TicketCategory.choices, required=False)

    def to_internal_value(self, data):
        allowed = set(self.fields) | {PORTAL_HONEYPOT_FIELD}
        unknown = set(data) - allowed if isinstance(data, dict) else set()
        if unknown:
            raise serializers.ValidationError(
                {n: "Unknown field." for n in sorted(unknown)}
            )
        return super().to_internal_value(data)
