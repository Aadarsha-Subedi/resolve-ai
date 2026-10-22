from django.db import transaction
from django.dispatch import receiver

from knowledge.services import ask_history, category_service, upload_service
from knowledge.tasks import reindex_workspace
from workspaces.services import hooks as workspace_hooks


@receiver(workspace_hooks.workspace_event)
def on_workspace_event(sender, workspace, action, actor=None, **kwargs) -> None:
    if action == workspace_hooks.ACTION_CREATED:
        category_service.seed_defaults(workspace.id)
    elif action == workspace_hooks.ACTION_UPDATED:
        fields = kwargs.get("metadata", {}).get("fields", [])
        if "search_language" in fields:
            transaction.on_commit(lambda: reindex_workspace.delay(str(workspace.id)))
    elif action == workspace_hooks.ACTION_MEMBER_LEFT:
        ask_history.delete_for_member(workspace.id, actor.id)
    elif action == workspace_hooks.ACTION_MEMBER_REMOVED:
        ask_history.delete_for_member(workspace.id, kwargs["metadata"]["user_id"])
    elif action == workspace_hooks.ACTION_PURGED:
        # Runs before the rows are deleted, so the storage keys are still known.
        # Article bodies and chunks are database rows and go with the workspace.
        upload_service.purge_workspace_objects(workspace.id)
