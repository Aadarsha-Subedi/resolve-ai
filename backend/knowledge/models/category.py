import uuid

from django.db import models

from common.models import TimeStampModel
from knowledge.constants.settings import (
    CATEGORY_NAME_MAX_LENGTH,
    CATEGORY_SLUG_MAX_LENGTH,
)


class KnowledgeCategory(TimeStampModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="knowledge_categories",
    )
    name = models.CharField(max_length=CATEGORY_NAME_MAX_LENGTH)
    slug = models.SlugField(max_length=CATEGORY_SLUG_MAX_LENGTH)

    class Meta:
        db_table = "knowledge_category"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "slug"], name="unique_category_slug_per_workspace"
            )
        ]
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name
