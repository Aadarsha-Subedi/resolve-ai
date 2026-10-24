"""One call for the dashboard screen. Cached for a few seconds per workspace and query."""

from dataclasses import dataclass

from django.utils import timezone

from accounts.models import User
from audit.constants import dashboard as config
from audit.serializers.dashboard_responses import (
    activity_item,
    recent_item,
    waiting_item,
)
from audit.services import dashboard_metrics as metrics
from audit.services.dashboard_period import Period, resolve
from common.cache.manager import cache_manager
from workspaces.constants import permissions
from workspaces.services import access


@dataclass(frozen=True)
class DashboardResult:
    data: dict
    cached: bool


def _cache_key(workspace_id, period: Period, query: dict, sections) -> str:
    """Normalised: equal queries (including `period=30d` against the same dates sent
    as from/to) share one entry, whatever order the parameters arrived in."""
    return cache_manager.build_scoped_key(
        config.CACHE_NAMESPACE,
        str(workspace_id),
        period.tz_name,
        period.start.isoformat(),
        period.end.isoformat(),
        ",".join(sections),
        str(query["recent_limit"]),
        str(query["waiting_limit"]),
        str(query["activity_limit"]),
    )


def _build(workspace_id, period: Period, query: dict, sections) -> dict:
    previous = period.previous
    data: dict = {
        "generated_at": timezone.now().isoformat(),
        "period": {
            "key": period.key,
            "from": period.start.isoformat(),
            "to": period.end.isoformat(),
            "days": period.days,
            "tz": period.tz_name,
            "previous": {
                "from": previous.start.isoformat(),
                "to": previous.end.isoformat(),
            },
        },
    }
    if config.SECTION_SUMMARY in sections:
        data["summary"] = metrics.summary(workspace_id, period)
    if config.SECTION_VOLUME in sections:
        data["volume"] = metrics.volume(workspace_id, period)
    if config.SECTION_RECENT in sections:
        rows = metrics.recent_tickets(workspace_id, query["recent_limit"])
        data["recent_tickets"] = {"items": [recent_item(t) for t in rows]}
    if config.SECTION_WAITING in sections:
        rows, total = metrics.waiting_tickets(workspace_id, query["waiting_limit"])
        data["waiting"] = {"total": total, "items": [waiting_item(t) for t in rows]}
    if config.SECTION_ACTIVITY in sections:
        rows = metrics.activity(workspace_id, query["activity_limit"])
        data["activity"] = {"items": [activity_item(e) for e in rows]}
    return data


def get_dashboard(user: User, workspace_id, query: dict) -> DashboardResult:
    # Access is checked on every call, before the cache is consulted.
    access.require_permission(user, workspace_id, permissions.DASHBOARD_VIEW)
    period = resolve(query)
    sections = query.get("include", config.SECTIONS)
    hit = True

    def load() -> dict:
        nonlocal hit
        hit = False
        return _build(workspace_id, period, query, sections)

    data = cache_manager.get_or_set(
        _cache_key(workspace_id, period, query, sections),
        load,
        timeout=config.CACHE_TTL_SECONDS,
    )
    return DashboardResult(data=data, cached=hit)
