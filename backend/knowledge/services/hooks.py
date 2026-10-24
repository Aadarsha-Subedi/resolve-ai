"""Audit extension point (feature 2 subscribes to `knowledge_event` when it is built).
Metadata never carries article text or file contents."""

from django.dispatch import Signal

SENDER = "knowledge"
knowledge_event = Signal()  # kwargs: workspace, actor, action, metadata

ACTION_ARTICLE_CREATED = "article.created"
ACTION_ARTICLE_UPDATED = "article.updated"
ACTION_ARTICLE_PUBLISHED = "article.published"
ACTION_ARTICLE_UNPUBLISHED = "article.unpublished"
ACTION_ARTICLE_ARCHIVED = "article.archived"
ACTION_ARTICLE_DELETED = "article.deleted"
ACTION_CATEGORY_CREATED = "category.created"
ACTION_CATEGORY_UPDATED = "category.updated"
ACTION_CATEGORY_DELETED = "category.deleted"
ACTION_UPLOAD_CONFIRMED = "upload.confirmed"
ACTION_UPLOAD_DELETED = "upload.deleted"


def emit(workspace, actor, action: str, **metadata) -> None:
    knowledge_event.send(
        sender=SENDER,
        workspace=workspace,
        actor=actor,
        action=action,
        metadata=metadata,
    )
