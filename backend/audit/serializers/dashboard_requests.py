from datetime import timedelta
from zoneinfo import ZoneInfo

from rest_framework import serializers

from audit.constants import messages
from audit.constants.dashboard import (
    DEFAULT_ACTIVITY_LIMIT,
    DEFAULT_RECENT_LIMIT,
    DEFAULT_TIMEZONE,
    DEFAULT_WAITING_LIMIT,
    MAX_CUSTOM_DAYS,
    MAX_LIMIT,
    MIN_LIMIT,
    PERIOD_DAYS,
    SECTIONS,
    TIMEZONE_ALIASES,
)
from common.serializers.base import StrictSerializer


class DashboardQuerySerializer(StrictSerializer):
    """Query string of the dashboard. Unknown parameters are rejected."""

    period = serializers.ChoiceField(required=False, choices=sorted(PERIOD_DAYS))
    tz = serializers.CharField(required=False, default=DEFAULT_TIMEZONE, max_length=64)
    include = serializers.CharField(required=False, max_length=200)
    recent_limit = serializers.IntegerField(
        required=False,
        default=DEFAULT_RECENT_LIMIT,
        min_value=MIN_LIMIT,
        max_value=MAX_LIMIT,
    )
    waiting_limit = serializers.IntegerField(
        required=False,
        default=DEFAULT_WAITING_LIMIT,
        min_value=MIN_LIMIT,
        max_value=MAX_LIMIT,
    )
    activity_limit = serializers.IntegerField(
        required=False,
        default=DEFAULT_ACTIVITY_LIMIT,
        min_value=MIN_LIMIT,
        max_value=MAX_LIMIT,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # `from` is a Python keyword, so these two are declared by name here.
        self.fields["from"] = serializers.DateField(required=False)
        self.fields["to"] = serializers.DateField(required=False)

    def to_internal_value(self, data):
        # DRF treats `?name=` as "not sent" for optional fields; here it is an error.
        blank = sorted(name for name in data if data[name] == "")
        if blank:
            raise serializers.ValidationError(
                {name: messages.MESSAGE_VALUE_BLANK for name in blank}
            )
        return super().to_internal_value(data)

    def validate_tz(self, value: str) -> str:
        value = TIMEZONE_ALIASES.get(value.strip(), value.strip())
        try:
            ZoneInfo(value)
        except ValueError, OSError, KeyError:  # ZoneInfoNotFoundError is a KeyError
            raise serializers.ValidationError(messages.MESSAGE_TIMEZONE_INVALID)
        return value

    def validate_include(self, value: str) -> tuple[str, ...]:
        names = [part.strip() for part in value.split(",") if part.strip()]
        if not names:
            raise serializers.ValidationError(messages.MESSAGE_INCLUDE_EMPTY)
        for name in names:
            if name not in SECTIONS:
                raise serializers.ValidationError(
                    messages.MESSAGE_SECTION_UNKNOWN.format(
                        name=name, allowed=", ".join(SECTIONS)
                    )
                )
        return tuple(section for section in SECTIONS if section in names)

    def validate(self, attrs):
        start, end = attrs.get("from"), attrs.get("to")
        if "period" in attrs and (start or end):
            raise serializers.ValidationError(messages.MESSAGE_PERIOD_CONFLICT)
        if bool(start) != bool(end):
            raise serializers.ValidationError(messages.MESSAGE_RANGE_INCOMPLETE)
        if start and end:
            if start > end:
                raise serializers.ValidationError(messages.MESSAGE_RANGE_ORDER)
            if end - start > timedelta(days=MAX_CUSTOM_DAYS - 1):
                raise serializers.ValidationError(
                    messages.MESSAGE_RANGE_TOO_LONG.format(days=MAX_CUSTOM_DAYS)
                )
        return attrs
