"""Turns the validated query into a reporting window and its same-length predecessor."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo
from zoneinfo import ZoneInfo

from django.utils import timezone

from audit.constants.dashboard import CUSTOM_PERIOD, DEFAULT_PERIOD, PERIOD_DAYS


@dataclass(frozen=True)
class Period:
    key: str  # "7d" | "30d" | "90d" | "custom"
    tz_name: str
    start: date  # first local day, inclusive
    end: date  # last local day, inclusive
    days: int

    @property
    def tz(self) -> tzinfo:
        return ZoneInfo(self.tz_name)

    @property
    def previous(self) -> Period:
        end = self.start - timedelta(days=1)
        return Period(
            self.key, self.tz_name, end - timedelta(days=self.days - 1), end, self.days
        )

    def bounds(self) -> tuple[datetime, datetime]:
        """[start, end) as aware datetimes at local midnight."""
        tz = self.tz
        return (
            datetime.combine(self.start, time.min, tzinfo=tz),
            datetime.combine(self.end + timedelta(days=1), time.min, tzinfo=tz),
        )


def resolve(query: dict) -> Period:
    tz_name = query["tz"]
    start, end = query.get("from"), query.get("to")
    if start and end:
        return Period(CUSTOM_PERIOD, tz_name, start, end, (end - start).days + 1)
    key = query.get("period", DEFAULT_PERIOD)
    days = PERIOD_DAYS[key]
    today = timezone.now().astimezone(ZoneInfo(tz_name)).date()
    return Period(key, tz_name, today - timedelta(days=days - 1), today, days)
