from datetime import date

from django.db.models import QuerySet

from accounts.models import User
from audit.models import AuditEvent
from workspaces.constants import permissions
from workspaces.services import access


def list_events(
    user: User,
    workspace_id,
    action: str | None = None,
    action_prefix: str | None = None,
    actor=None,
    target_type: str | None = None,
    target_id: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
) -> QuerySet[AuditEvent]:
    """The workspace's audit log, newest first. Owner only (404 for non-members, 403 for members)."""
    access.require_permission(user, workspace_id, permissions.AUDIT_VIEW)
    queryset = AuditEvent.objects.filter(workspace_id=workspace_id)
    if action:
        queryset = queryset.filter(action=action)
    if action_prefix:
        queryset = queryset.filter(action__startswith=action_prefix)
    if actor:
        queryset = queryset.filter(actor_user_id=actor)
    if target_type:
        queryset = queryset.filter(target_type=target_type)
    if target_id:
        queryset = queryset.filter(target_id=target_id)
    if created_from:
        queryset = queryset.filter(created_at__date__gte=created_from)
    if created_to:
        queryset = queryset.filter(created_at__date__lte=created_to)
    return queryset.select_related("actor_user")
