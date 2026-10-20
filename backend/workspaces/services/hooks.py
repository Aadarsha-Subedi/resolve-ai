"""Audit extension point (feature 2 subscribes to `workspace_event` when it is built).

Metadata never carries tokens, raw invitation addresses or other secrets.
"""

from django.dispatch import Signal

SENDER = "workspaces"
workspace_event = Signal()  # kwargs: workspace, actor, action, metadata

ACTION_CREATED = "workspace.created"
ACTION_UPDATED = "workspace.updated"
ACTION_DELETED = "workspace.deleted"
ACTION_PURGED = "workspace.purged"
ACTION_MEMBER_JOINED = "member.joined"
ACTION_MEMBER_REMOVED = "member.removed"
ACTION_MEMBER_LEFT = "member.left"
ACTION_OWNERSHIP_TRANSFERRED = "ownership.transferred"
ACTION_JOIN_LINK_CREATED = "join_link.created"
ACTION_JOIN_LINK_REVOKED = "join_link.revoked"
ACTION_INVITATION_CREATED = "invitation.created"
ACTION_INVITATION_REVOKED = "invitation.revoked"
ACTION_INVITATION_ACCEPTED = "invitation.accepted"
ACTION_INVITATION_DECLINED = "invitation.declined"
ACTION_LOGO_CHANGED = "workspace.logo_changed"


def emit(workspace, actor, action: str, **metadata) -> None:
    workspace_event.send(
        sender=SENDER,
        workspace=workspace,
        actor=actor,
        action=action,
        metadata=metadata,
    )
