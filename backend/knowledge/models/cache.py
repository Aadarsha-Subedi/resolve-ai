import uuid

from django.db import models
from pgvector.django import VectorField

from common.llm.constants import EMBEDDING_DIMENSIONS


class AskCacheEntry(models.Model):
    """A question that was answered (`answered` only), with its embedding and the exact payload
    the user was shown. Workspace-scoped; deleted whenever the workspace's articles or uploads
    change, so a cached answer never outlives the passages it was written from."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="+"
    )
    question = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, editable=False)
    embedding_model = models.CharField(max_length=60)
    llm_model = models.CharField(max_length=100)  # "<provider>:<model>" that wrote it
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "knowledge_ask_cache"
        indexes = [
            models.Index(
                fields=["workspace", "-created_at"], name="knowledge_ask_cache_ws"
            )
        ]
