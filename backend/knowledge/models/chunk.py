import uuid

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models

from knowledge.constants.settings import CHUNK_HEADING_PATH_MAX_LENGTH
from workspaces.constants.settings import (
    DEFAULT_SEARCH_LANGUAGE,
    SEARCH_LANGUAGE_CHOICES,
    SEARCH_LANGUAGE_MAX_LENGTH,
)


class KnowledgeChunk(models.Model):
    """A passage of one article, used for search and citations.

    Rows are written only by `knowledge.services.chunk_service`, in the same transaction
    as the article change, so they never drift from the article. `search_vector` is
    filled by that service (Postgres only; it stays NULL on SQLite) using
    `search_language`, a copy of the workspace language at the time of writing.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="+"
    )
    article = models.ForeignKey(
        "knowledge.KnowledgeArticle", on_delete=models.CASCADE, related_name="chunks"
    )
    position = models.PositiveIntegerField()
    heading_path = models.CharField(max_length=CHUNK_HEADING_PATH_MAX_LENGTH)
    text = models.TextField()
    search_language = models.CharField(
        max_length=SEARCH_LANGUAGE_MAX_LENGTH,
        choices=SEARCH_LANGUAGE_CHOICES,
        default=DEFAULT_SEARCH_LANGUAGE,
    )
    search_vector = SearchVectorField(null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "knowledge_chunk"
        ordering = ["article_id", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["article", "position"], name="unique_chunk_position"
            )
        ]
        indexes = [
            models.Index(
                fields=["workspace", "article", "position"],
                name="knowledge_chunk_ws_art_pos",
            ),
            GinIndex(fields=["search_vector"], name="knowledge_chunk_search_gin"),
        ]
