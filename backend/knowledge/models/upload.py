import uuid

from django.conf import settings
from django.db import models

from common.models import TimeStampModel
from knowledge.constants.enums import IndexStatus, UploadStatus
from knowledge.constants.settings import UPLOAD_FILENAME_MAX_LENGTH


class KnowledgeUpload(TimeStampModel):
    """A PDF, DOCX, Markdown or text document. The row exists as
    PENDING from the moment space is reserved until the browser upload is confirmed."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="knowledge_uploads",
    )
    filename = models.CharField(max_length=UPLOAD_FILENAME_MAX_LENGTH)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField()
    storage_key = models.CharField(max_length=300, unique=True)
    status = models.CharField(
        max_length=10, choices=UploadStatus.choices, default=UploadStatus.PENDING
    )
    # Text extraction and search indexing (done in the background after the upload is confirmed).
    index_status = models.CharField(
        max_length=10, choices=IndexStatus.choices, default=IndexStatus.PENDING
    )
    index_error = models.CharField(
        max_length=40, blank=True, default=""
    )  # an error code, never text
    indexed_at = models.DateTimeField(null=True, blank=True)
    extracted_key = models.CharField(max_length=300, blank=True, default="")
    page_count = models.PositiveIntegerField(null=True, blank=True)
    # Every file is filed under a category; a deleted category leaves the file uncategorized.
    category = models.ForeignKey(
        "knowledge.KnowledgeCategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploads",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "knowledge_upload"
        indexes = [models.Index(fields=["workspace", "status", "-created_at"])]
