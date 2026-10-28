from django.db import transaction
from django.dispatch import receiver

from knowledge.services import (
    ask_history,
    cache_service,
    category_service,
    hooks,
    upload_service,
)
from knowledge.tasks import reindex_workspace
from workspaces.services import hooks as workspace_hooks


@receiver(workspace_hooks.workspace_event)
def on_workspace_event(sender, workspace, action, actor=None, **kwargs) -> None:
    if action == workspace_hooks.ACTION_CREATED:
        category_service.seed_defaults(workspace.id)
    elif action == workspace_hooks.ACTION_UPDATED:
        fields = kwargs.get("metadata", {}).get("fields", [])
        if "search_language" in fields:
            cache_service.clear(workspace.id)
            transaction.on_commit(lambda: reindex_workspace.delay(str(workspace.id)))
    elif action == workspace_hooks.ACTION_MEMBER_LEFT:
        ask_history.delete_for_member(workspace.id, actor.id)
    elif action == workspace_hooks.ACTION_MEMBER_REMOVED:
        ask_history.delete_for_member(workspace.id, kwargs["metadata"]["user_id"])
    elif action == workspace_hooks.ACTION_PURGED:
        # Runs before the rows are deleted, so the storage keys are still known.
        # Article bodies and chunks are database rows and go with the workspace.
        upload_service.purge_workspace_objects(workspace.id)


# Changes that alter which passages exist or what they say: cached answers may no longer hold.
_CACHE_CLEARING_ACTIONS = frozenset(
    {
        hooks.ACTION_ARTICLE_UPDATED,
        hooks.ACTION_ARTICLE_PUBLISHED,
        hooks.ACTION_ARTICLE_UNPUBLISHED,
        hooks.ACTION_ARTICLE_ARCHIVED,
        hooks.ACTION_ARTICLE_DELETED,
        hooks.ACTION_UPLOAD_DELETED,
    }
)


@receiver(hooks.knowledge_event)
def on_knowledge_event(sender, workspace, action, **kwargs) -> None:
    if action in _CACHE_CLEARING_ACTIONS:
        transaction.on_commit(lambda: cache_service.clear(workspace.id))
