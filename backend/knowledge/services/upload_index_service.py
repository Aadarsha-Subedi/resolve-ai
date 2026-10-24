"""Reads an uploaded document in the background and records the result on its row.

State machine of `KnowledgeUpload.index_status`:
PENDING -> INDEXING -> INDEXED, or FAILED (with `index_error` set to an error code).
A claim is one conditional UPDATE, so two workers never index the same upload at once.
Errors the document itself causes (damaged, empty, too big, timed out) end in FAILED
without a retry; any other error propagates so the Celery task retries it.
"""

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from common.documents import DocumentEmptyError, DocumentError, get_parser
from common.storage import get_storage
from knowledge.constants.enums import IndexStatus, UploadStatus
from knowledge.constants.settings import (
    EXTRACTED_CONTENT_TYPE,
    EXTRACTED_KEY,
    INDEX_ERROR_FAILED,
    INDEX_REQUEUE_AFTER_SECONDS,
    INDEX_STALE_SECONDS,
)
from knowledge.models import KnowledgeUpload
from knowledge.services import chunk_service

logger = logging.getLogger(__name__)


def extracted_key_for(upload: KnowledgeUpload) -> str:
    return EXTRACTED_KEY.format(workspace_id=upload.workspace_id, upload_id=upload.id)


def _claim(upload_id, force: bool) -> KnowledgeUpload | None:
    """Move the upload to INDEXING. None when it is gone, not confirmed, or already being
    handled. `force` also re-runs INDEXED and FAILED uploads (the reindex command)."""
    stale = timezone.now() - timedelta(seconds=INDEX_STALE_SECONDS)
    startable = Q(index_status=IndexStatus.PENDING) | Q(
        index_status=IndexStatus.INDEXING, updated_at__lt=stale
    )
    if force:
        startable |= Q(index_status__in=[IndexStatus.INDEXED, IndexStatus.FAILED])
    claimed = KnowledgeUpload.objects.filter(
        startable, pk=upload_id, status=UploadStatus.READY
    ).update(
        index_status=IndexStatus.INDEXING, index_error="", updated_at=timezone.now()
    )
    if not claimed:
        return None
    return KnowledgeUpload.objects.get(pk=upload_id)


def mark_failed(upload_id, code: str) -> None:
    KnowledgeUpload.objects.filter(pk=upload_id).update(
        index_status=IndexStatus.FAILED, index_error=code, updated_at=timezone.now()
    )


def _back_to_pending(upload_id) -> None:
    """After an unexpected error: let the retry (or the sweeper) claim the upload again."""
    KnowledgeUpload.objects.filter(
        pk=upload_id, index_status=IndexStatus.INDEXING
    ).update(index_status=IndexStatus.PENDING, updated_at=timezone.now())


def index_upload(upload_id, force: bool = False) -> bool:
    """Read the document, store its text, and write its search passages. Returns True when
    the upload is INDEXED."""
    upload = _claim(upload_id, force)
    if upload is None:
        return False
    storage = get_storage()
    key = extracted_key_for(upload)
    try:
        parsed = get_parser(upload.content_type).parse(
            storage.read(upload.storage_key), upload.content_type
        )
        drafts = chunk_service.upload_drafts(upload, parsed)
        if not drafts:  # only headings, or nothing that can be searched
            raise DocumentEmptyError()
        storage.upload(key, parsed.markdown.encode("utf-8"), EXTRACTED_CONTENT_TYPE)
    except DocumentError as error:
        logger.warning("Upload %s could not be read: %s", upload.id, error.code)
        mark_failed(upload.id, error.code)
        return False
    except Exception:
        _back_to_pending(upload.id)
        raise
    numbered = [page.number for page in parsed.pages if page.number is not None]
    try:
        with transaction.atomic():
            done = KnowledgeUpload.objects.filter(
                pk=upload.id, index_status=IndexStatus.INDEXING
            ).update(
                index_status=IndexStatus.INDEXED,
                index_error="",
                extracted_key=key,
                page_count=max(numbered) if numbered else None,
                indexed_at=timezone.now(),
                updated_at=timezone.now(),
            )
            if done:  # chunks and status are saved together or not at all
                chunk_service.rebuild_upload_chunks(upload, drafts)
    except Exception:
        _back_to_pending(upload.id)
        raise
    if not done:  # deleted (or taken over) while we were reading it
        storage.delete(key)
        return False
    return True


def record_unexpected_failure(upload_id) -> None:
    """The task gave up after its retries."""
    mark_failed(upload_id, INDEX_ERROR_FAILED)


def requeue_candidates():
    """Confirmed uploads whose indexing never started or was abandoned (lost message,
    worker killed). The sweeper queues them again."""
    now = timezone.now()
    waiting = timezone.now() - timedelta(seconds=INDEX_REQUEUE_AFTER_SECONDS)
    stale = now - timedelta(seconds=INDEX_STALE_SECONDS)
    return KnowledgeUpload.objects.filter(
        Q(index_status=IndexStatus.PENDING, updated_at__lt=waiting)
        | Q(index_status=IndexStatus.INDEXING, updated_at__lt=stale),
        status=UploadStatus.READY,
    ).values_list("id", flat=True)
