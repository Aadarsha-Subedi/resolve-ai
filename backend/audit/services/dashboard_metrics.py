"""Read queries behind the dashboard. Every function is one fixed query (or two) over
canonical ticket records and is scoped by workspace; none loops per row."""

from datetime import date, timedelta

from django.db.models import Count, F, Q
from django.db.models.functions import TruncDate

from audit.constants.dashboard import BUCKET_WEEK_DAYS, DAILY_BUCKET_MAX_DAYS
from audit.services.dashboard_period import Period
from tickets.constants.enums import EventType, TicketPriority, TicketStatus
from tickets.models import Ticket, TicketEvent

ACTIVE_STATUSES = (TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.PENDING)
_ACTIVE = Q(status__in=ACTIVE_STATUSES)
# Same rule as Ticket.waiting_for_reply, only on active tickets.
_WAITING = (
    _ACTIVE
    & Q(last_customer_message_at__isnull=False)
    & (
        Q(last_agent_reply_at__isnull=True)
        | Q(last_customer_message_at__gt=F("last_agent_reply_at"))
    )
)
_CHANGE_EVENTS = (
    EventType.STATUS_CHANGED,
    EventType.PRIORITY_CHANGED,
    EventType.CATEGORY_CHANGED,
)


def _in_window(field: str, period: Period) -> Q:
    start, end = period.bounds()
    return Q(**{f"{field}__gte": start, f"{field}__lt": end})


def summary(workspace_id, period: Period) -> dict:
    current, previous = period, period.previous
    totals = Ticket.objects.filter(workspace_id=workspace_id).aggregate(
        active=Count("pk", filter=_ACTIVE),
        open=Count("pk", filter=Q(status=TicketStatus.OPEN)),
        in_progress=Count("pk", filter=Q(status=TicketStatus.IN_PROGRESS)),
        pending=Count("pk", filter=Q(status=TicketStatus.PENDING)),
        urgent=Count("pk", filter=_ACTIVE & Q(priority=TicketPriority.URGENT)),
        high=Count("pk", filter=_ACTIVE & Q(priority=TicketPriority.HIGH)),
        waiting_for_reply=Count("pk", filter=_WAITING),
        created_current=Count("pk", filter=_in_window("created_at", current)),
        created_previous=Count("pk", filter=_in_window("created_at", previous)),
        resolved_current=Count("pk", filter=_in_window("resolved_at", current)),
        resolved_previous=Count("pk", filter=_in_window("resolved_at", previous)),
    )
    return {
        "active": totals["active"],
        "by_status": {
            "open": totals["open"],
            "in_progress": totals["in_progress"],
            "pending": totals["pending"],
        },
        "urgent": totals["urgent"],
        "high": totals["high"],
        "waiting_for_reply": totals["waiting_for_reply"],
        "created": {
            "current": totals["created_current"],
            "previous": totals["created_previous"],
        },
        "resolved": {
            "current": totals["resolved_current"],
            "previous": totals["resolved_previous"],
        },
    }


def _daily_counts(workspace_id, period: Period, field: str) -> dict[date, int]:
    rows = (
        Ticket.objects.filter(_in_window(field, period), workspace_id=workspace_id)
        .annotate(day=TruncDate(field, tzinfo=period.tz))
        .values("day")
        .annotate(total=Count("pk"))
        .order_by()
    )
    return {row["day"]: row["total"] for row in rows}


def volume(workspace_id, period: Period) -> dict:
    """Created and resolved per bucket, zero-filled: one bucket per day, or per
    7 days counted from the period start when the period is longer than a month."""
    created = _daily_counts(workspace_id, period, "created_at")
    resolved = _daily_counts(workspace_id, period, "resolved_at")
    daily = period.days <= DAILY_BUCKET_MAX_DAYS
    width = 1 if daily else BUCKET_WEEK_DAYS
    buckets = []
    for offset in range(0, period.days, width):
        first = period.start + timedelta(days=offset)
        last = min(first + timedelta(days=width - 1), period.end)
        days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
        buckets.append(
            {
                "start": first.isoformat(),
                "end": last.isoformat(),
                "created": sum(created.get(day, 0) for day in days),
                "resolved": sum(resolved.get(day, 0) for day in days),
            }
        )
    return {"granularity": "day" if daily else "week", "buckets": buckets}


def recent_tickets(workspace_id, limit: int) -> list[Ticket]:
    return list(
        Ticket.objects.filter(workspace_id=workspace_id).order_by(
            "-last_activity_at", "-number"
        )[:limit]
    )


def waiting_tickets(workspace_id, limit: int) -> tuple[list[Ticket], int]:
    """Active tickets whose last public message is the customer's, longest-waiting first."""
    queryset = Ticket.objects.filter(_WAITING, workspace_id=workspace_id)
    rows = list(queryset.order_by("last_customer_message_at", "number")[:limit])
    return rows, queryset.count()


def activity(workspace_id, limit: int) -> list[TicketEvent]:
    return list(
        TicketEvent.objects.filter(workspace_id=workspace_id)
        .select_related("ticket", "actor_user")
        .order_by("-created_at", "-id")[:limit]
    )


def is_change_event(event_type: str) -> bool:
    return event_type in _CHANGE_EVENTS
