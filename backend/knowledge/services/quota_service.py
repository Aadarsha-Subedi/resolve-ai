"""Per-workspace storage quota (50 MB, WORKSPACE_STORAGE_QUOTA_BYTES).

`Workspace.storage_used_bytes` is changed only here, with single conditional UPDATE
statements, so two concurrent uploads can never both squeeze under the limit.
"""

from django.conf import settings
from django.db.models import F, Value
from django.db.models.functions import Greatest

from common.exception.domain import ConflictException, PayloadTooLargeException
from knowledge.constants import errors, messages
from knowledge.models import KnowledgeArticle
from workspaces.models import Workspace


def limit_bytes() -> int:
    return settings.WORKSPACE_STORAGE_QUOTA_BYTES


def ensure_article_capacity(workspace_id) -> None:
    """Raise 409 when the workspace already holds the maximum number of articles.
    Call inside a transaction: the workspace row is locked so two simultaneous creates
    cannot both pass the check."""
    Workspace.all_objects.select_for_update().filter(pk=workspace_id).first()
    limit = settings.WORKSPACE_MAX_ARTICLES
    if KnowledgeArticle.objects.filter(workspace_id=workspace_id).count() >= limit:
        raise ConflictException(
            messages.MESSAGE_ARTICLE_LIMIT_REACHED.format(limit=limit),
            error_code=errors.ERROR_ARTICLE_LIMIT_REACHED,
        )


def reserve(workspace_id, size: int) -> None:
    """Add `size` bytes to the usage, or raise 413 when it would not fit."""
    if size <= 0:
        return
    updated = Workspace.all_objects.filter(
        pk=workspace_id, storage_used_bytes__lte=limit_bytes() - size
    ).update(storage_used_bytes=F("storage_used_bytes") + size)
    if not updated:
        raise PayloadTooLargeException(
            messages.MESSAGE_QUOTA_EXCEEDED.format(
                limit_mb=limit_bytes() // (1024 * 1024)
            ),
            error_code=errors.ERROR_STORAGE_QUOTA_EXCEEDED,
        )


def release(workspace_id, size: int) -> None:
    """Give `size` bytes back (never below zero)."""
    if size <= 0:
        return
    Workspace.all_objects.filter(pk=workspace_id).update(
        storage_used_bytes=Greatest(F("storage_used_bytes") - size, Value(0))
    )


def usage(workspace_id) -> dict:
    used = Workspace.all_objects.values_list("storage_used_bytes", flat=True).get(
        pk=workspace_id
    )
    limit = limit_bytes()
    return {
        "used_bytes": used,
        "limit_bytes": limit,
        "remaining_bytes": max(limit - used, 0),
    }
