from django.dispatch import receiver

from tickets.services import ticket_service
from workspaces.services import hooks as workspace_hooks


@receiver(workspace_hooks.workspace_event)
def unassign_departed_member(
    sender, workspace, actor, action, metadata, **kwargs
) -> None:
    """A member who leaves or is removed no longer holds active tickets."""
    if action == workspace_hooks.ACTION_MEMBER_REMOVED:
        user_id, reason = metadata.get("user_id"), "member_removed"
    elif action == workspace_hooks.ACTION_MEMBER_LEFT:
        user_id, reason = actor.id, "member_left"
    else:
        return
    if user_id:
        ticket_service.unassign_departed_member(workspace.id, user_id, reason=reason)
