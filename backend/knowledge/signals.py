from django.dispatch import receiver

from knowledge.services import category_service, upload_service
from workspaces.services import hooks as workspace_hooks


@receiver(workspace_hooks.workspace_event)
def on_workspace_event(sender, workspace, action, **kwargs) -> None:
    if action == workspace_hooks.ACTION_CREATED:
        category_service.seed_defaults(workspace.id)
    elif action == workspace_hooks.ACTION_PURGED:
        # Runs before the rows are deleted, so the storage keys are still known.
        # Article bodies are database rows and go with the workspace.
        upload_service.purge_workspace_objects(workspace.id)
