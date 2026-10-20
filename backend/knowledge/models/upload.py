import uuid

from django.conf import settings
from django.db import models

from common.models import TimeStampModel
from knowledge.constants.enums import UploadStatus
from knowledge.constants.settings import UPLOAD_FILENAME_MAX_LENGTH


class KnowledgeUpload(TimeStampModel):
    """A PDF/TXT document. Stored only (no text extraction in v1). The row exists as
    PENDING from the moment space is reserved until the browser upload is confirmed."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="knowledge_uploads",
    )
    filename = models.CharField(max_length=UPLOAD_FILENAME_MAX_LENGTH)
    content_type = models.CharField(max_length=50)
    size_bytes = models.PositiveIntegerField()
    storage_key = models.CharField(max_length=300, unique=True)
    status = models.CharField(
        max_length=10, choices=UploadStatus.choices, default=UploadStatus.PENDING
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "knowledge_upload"
        indexes = [models.Index(fields=["workspace", "status", "-created_at"])]
