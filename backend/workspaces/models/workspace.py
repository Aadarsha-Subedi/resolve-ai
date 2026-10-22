import uuid

from django.conf import settings
from django.db import models

from common.models import SoftDeleteModel, TimeStampModel
from workspaces.constants.settings import (
    DEFAULT_SEARCH_LANGUAGE,
    NAME_MAX_LENGTH,
    SEARCH_LANGUAGE_CHOICES,
    SEARCH_LANGUAGE_MAX_LENGTH,
    SLUG_MAX_LENGTH,
)


class Workspace(SoftDeleteModel, TimeStampModel):
    """The tenant. Deleted workspaces are hidden at once and purged after the grace period."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    name = models.CharField(max_length=NAME_MAX_LENGTH)
    # Public locator, immutable after creation (the update serializer has no slug field).
    slug = models.SlugField(max_length=SLUG_MAX_LENGTH, unique=True, editable=False)
    logo_key = models.CharField(max_length=300, blank=True)
    portal_enabled = models.BooleanField(default=True)
    # Postgres text search configuration used for this workspace's full-text search.
    search_language = models.CharField(
        max_length=SEARCH_LANGUAGE_MAX_LENGTH,
        choices=SEARCH_LANGUAGE_CHOICES,
        default=DEFAULT_SEARCH_LANGUAGE,
    )
    # Last ticket number handed out; tickets.services.numbering is the only writer.
    last_ticket_number = models.PositiveIntegerField(default=0)
    # Bytes used by knowledge articles and uploads (logo excluded); changed only by
    # knowledge.services.quota_service with atomic conditional updates.
    storage_used_bytes = models.BigIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        db_table = "workspaces_workspace"

    def __str__(self) -> str:
        return self.slug
