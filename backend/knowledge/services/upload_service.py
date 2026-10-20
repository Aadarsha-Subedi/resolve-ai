import os
import re
import uuid

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from accounts.models import User
from common.exception.domain import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    ServiceUnavailableException,
)
from common.storage import get_storage
from common.storage.base import DirectUploadUnsupported
from knowledge.constants import errors, messages
from knowledge.constants.enums import UploadStatus
from knowledge.constants.settings import (
    DOWNLOAD_URL_EXPIRY_SECONDS,
    PDF_MAGIC,
    UPLOAD_CONTENT_TYPES,
    UPLOAD_FILENAME_MAX_LENGTH,
    UPLOAD_KEY,
    UPLOAD_MAX_BYTES,
    UPLOAD_PENDING_TTL_SECONDS,
    UPLOAD_URL_EXPIRY_SECONDS,
)
from knowledge.models import KnowledgeUpload
from knowledge.services import hooks, quota_service
from workspaces.constants import permissions
from workspaces.services import access

_UNSAFE = re.compile(r"[\x00-\x1f\x7f\\/:*?\"<>|]+")


def clean_filename(name: str, content_type: str) -> str:
    """Display name only (the storage key never uses it): no path, no control characters."""
    base = _UNSAFE.sub("_", os.path.basename(name.replace("\\", "/"))).strip(" .")
    extension = "." + UPLOAD_CONTENT_TYPES[content_type]
    base = base[: UPLOAD_FILENAME_MAX_LENGTH - len(extension)] or "document"
    return base if base.lower().endswith(extension) else base + extension


def create_upload(
    user: User, workspace_id, filename: str, content_type: str, size: int
) -> tuple[KnowledgeUpload, dict]:
    """Reserve quota, create the PENDING row and hand out a signed PUT URL."""
    access.require_permission(user, workspace_id, permissions.KNOWLEDGE_MANAGE)
    upload_id = uuid.uuid7()
    key = UPLOAD_KEY.format(
        workspace_id=workspace_id,
        upload_id=upload_id,
        extension=UPLOAD_CONTENT_TYPES[content_type],
    )
    with transaction.atomic():
        quota_service.reserve(workspace_id, size)
        upload = KnowledgeUpload.objects.create(
            id=upload_id,
            workspace_id=workspace_id,
            filename=clean_filename(filename, content_type),
            content_type=content_type,
            size_bytes=size,
            storage_key=key,
            uploaded_by=user,
        )
        try:
            url = get_storage().presign_put(
                key, content_type, size, UPLOAD_URL_EXPIRY_SECONDS
            )
        except DirectUploadUnsupported:
            raise ServiceUnavailableException(
                messages.MESSAGE_UPLOAD_UNSUPPORTED,
                error_code=errors.ERROR_UPLOAD_UNSUPPORTED,
            ) from None
    return upload, {
        "upload_url": url,
        "expires_in": UPLOAD_URL_EXPIRY_SECONDS,
        "headers": {"Content-Type": content_type},
    }


def _get(workspace_id, upload_id) -> KnowledgeUpload:
    upload = KnowledgeUpload.objects.filter(
        workspace_id=workspace_id, pk=upload_id
    ).first()
    if upload is None:
        raise NotFoundException(messages.MESSAGE_UPLOAD_NOT_FOUND)
    return upload


def _discard(upload: KnowledgeUpload) -> None:
    """Drop an upload: delete the object, free the quota, remove the row."""
    key, size, workspace_id = upload.storage_key, upload.size_bytes, upload.workspace_id
    with transaction.atomic():
        upload.delete()
        quota_service.release(workspace_id, size)
    get_storage().delete(key)


def confirm_upload(user: User, workspace_id, upload_id) -> KnowledgeUpload:
    """After the browser PUT: the object must exist with exactly the declared size and type."""
    membership = access.require_permission(
        user, workspace_id, permissions.KNOWLEDGE_MANAGE
    )
    upload = _get(workspace_id, upload_id)
    if upload.status != UploadStatus.PENDING:
        raise ConflictException(
            messages.MESSAGE_UPLOAD_NOT_PENDING,
            error_code=errors.ERROR_UPLOAD_NOT_PENDING,
        )
    storage = get_storage()
    info = storage.head(upload.storage_key)
    valid = (
        info is not None
        and info.size == upload.size_bytes
        and info.size <= UPLOAD_MAX_BYTES
        and info.content_type == upload.content_type
    )
    if valid and upload.content_type == "application/pdf":
        valid = storage.read_range(upload.storage_key, len(PDF_MAGIC)) == PDF_MAGIC
    if not valid:
        _discard(upload)  # never keep an object we refuse to use
        raise BadRequestException(
            messages.MESSAGE_UPLOAD_INVALID, error_code=errors.ERROR_UPLOAD_INVALID
        )
    upload.status = UploadStatus.READY
    upload.save(update_fields=["status", "updated_at"])
    hooks.emit(
        membership.workspace,
        user,
        hooks.ACTION_UPLOAD_CONFIRMED,
        target_id=str(upload.id),
    )
    return upload


def list_uploads(user: User, workspace_id) -> QuerySet[KnowledgeUpload]:
    access.require_permission(user, workspace_id, permissions.KNOWLEDGE_VIEW)
    return KnowledgeUpload.objects.filter(
        workspace_id=workspace_id, status=UploadStatus.READY
    ).order_by("-created_at", "id")


def download_url(user: User, workspace_id, upload_id) -> dict:
    access.require_permission(user, workspace_id, permissions.KNOWLEDGE_VIEW)
    upload = _get(workspace_id, upload_id)
    if upload.status != UploadStatus.READY:
        raise NotFoundException(messages.MESSAGE_UPLOAD_NOT_FOUND)
    try:
        url = get_storage().presign_get(
            upload.storage_key,
            DOWNLOAD_URL_EXPIRY_SECONDS,
            filename=upload.filename,
            inline=False,
        )
    except DirectUploadUnsupported:
        raise ServiceUnavailableException(
            messages.MESSAGE_UPLOAD_UNSUPPORTED,
            error_code=errors.ERROR_UPLOAD_UNSUPPORTED,
        ) from None
    return {"download_url": url, "expires_in": DOWNLOAD_URL_EXPIRY_SECONDS}


def delete_upload(user: User, workspace_id, upload_id) -> None:
    membership = access.require_permission(
        user, workspace_id, permissions.KNOWLEDGE_MANAGE
    )
    _discard(_get(workspace_id, upload_id))
    hooks.emit(
        membership.workspace,
        user,
        hooks.ACTION_UPLOAD_DELETED,
        target_id=str(upload_id),
    )


def release_stale_uploads() -> int:
    """Remove PENDING uploads that were never confirmed, freeing their reserved space."""
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(seconds=UPLOAD_PENDING_TTL_SECONDS)
    count = 0
    stale = KnowledgeUpload.objects.filter(
        status=UploadStatus.PENDING, created_at__lte=cutoff
    )
    for upload in stale.iterator():
        _discard(upload)
        count += 1
    return count


def purge_workspace_objects(workspace_id) -> None:
    storage = get_storage()
    for key in KnowledgeUpload.objects.filter(workspace_id=workspace_id).values_list(
        "storage_key", flat=True
    ):
        storage.delete(key)
