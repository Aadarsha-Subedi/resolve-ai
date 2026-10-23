from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from knowledge.constants.settings import (
    INDEX_ERROR_TIMEOUT,
    INDEX_MAX_RETRIES,
    INDEX_QUEUE,
    INDEX_RETRY_BACKOFF_SECONDS,
    INDEX_SOFT_TIME_LIMIT_SECONDS,
    INDEX_TIME_LIMIT_SECONDS,
    TASK_INDEX_UPLOAD,
    TASK_REINDEX_WORKSPACE,
    TASK_RELEASE_STALE_UPLOADS,
    TASK_REQUEUE_UNINDEXED_UPLOADS,
)
from knowledge.services import chunk_service, upload_index_service, upload_service


@shared_task(name=TASK_RELEASE_STALE_UPLOADS)
def release_stale_uploads() -> int:
    return upload_service.release_stale_uploads()


@shared_task(name=TASK_REINDEX_WORKSPACE)
def reindex_workspace(workspace_id: str) -> int:
    """Run after a workspace changes its search language."""
    return chunk_service.reindex_language(workspace_id)


@shared_task(
    name=TASK_INDEX_UPLOAD,
    bind=True,
    queue=INDEX_QUEUE,
    soft_time_limit=INDEX_SOFT_TIME_LIMIT_SECONDS,
    time_limit=INDEX_TIME_LIMIT_SECONDS,
    max_retries=INDEX_MAX_RETRIES,
)
def index_upload(self, upload_id: str, force: bool = False) -> bool:
    """Read an uploaded document and store its text. Unexpected errors are retried with a
    growing delay; after the last retry the upload is marked FAILED."""
    try:
        return upload_index_service.index_upload(upload_id, force=force)
    except SoftTimeLimitExceeded:
        upload_index_service.mark_failed(upload_id, INDEX_ERROR_TIMEOUT)
        return False
    except Exception as error:
        if self.request.retries >= self.max_retries:
            upload_index_service.record_unexpected_failure(upload_id)
            raise
        raise self.retry(
            exc=error,
            countdown=INDEX_RETRY_BACKOFF_SECONDS * (self.request.retries + 1),
        ) from error


@shared_task(name=TASK_REQUEUE_UNINDEXED_UPLOADS)
def requeue_unindexed_uploads() -> int:
    """Safety net for lost messages: queue uploads that never got indexed."""
    ids = list(upload_index_service.requeue_candidates())
    for upload_id in ids:
        index_upload.delay(str(upload_id))
    return len(ids)
