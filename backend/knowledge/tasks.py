from celery import shared_task

from knowledge.constants.settings import (
    TASK_REINDEX_WORKSPACE,
    TASK_RELEASE_STALE_UPLOADS,
)
from knowledge.services import chunk_service, upload_service


@shared_task(name=TASK_RELEASE_STALE_UPLOADS)
def release_stale_uploads() -> int:
    return upload_service.release_stale_uploads()


@shared_task(name=TASK_REINDEX_WORKSPACE)
def reindex_workspace(workspace_id: str) -> int:
    """Run after a workspace changes its search language."""
    return chunk_service.reindex_language(workspace_id)
