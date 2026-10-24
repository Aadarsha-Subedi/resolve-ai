from django.dispatch import receiver

from ai.services import settings_service
from workspaces.services import hooks as workspace_hooks


@receiver(workspace_hooks.workspace_event)
def on_workspace_event(sender, workspace, actor, action, metadata, **kwargs) -> None:
    """A member who leaves or is removed takes their stored API key with them."""
    if action == workspace_hooks.ACTION_MEMBER_LEFT:
        settings_service.delete_for_member(workspace.id, actor.id)
    elif action == workspace_hooks.ACTION_MEMBER_REMOVED:
        settings_service.delete_for_member(workspace.id, metadata["user_id"])
