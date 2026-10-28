import uuid

from django.conf import settings
from django.db import models

from ai.constants.settings import (
    MODEL_MAX_LENGTH,
    PROVIDER_MAX_LENGTH,
    USAGE_ERROR_MAX_LENGTH,
    USAGE_FEATURE_MAX_LENGTH,
    USAGE_OUTCOME_MAX_LENGTH,
)


class AIUsageLog(models.Model):
    """One AI call made for a workspace, shown to its owner: answered from the cache, sent to
    the provider, or failed. `answer` and `details` (cited passages, cache similarity) are
    filled for the Ask feature only."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="+"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    feature = models.CharField(max_length=USAGE_FEATURE_MAX_LENGTH)
    outcome = models.CharField(max_length=USAGE_OUTCOME_MAX_LENGTH)
    provider = models.CharField(max_length=PROVIDER_MAX_LENGTH, blank=True, default="")
    model = models.CharField(max_length=MODEL_MAX_LENGTH, blank=True, default="")
    question = models.TextField(blank=True, default="")
    answer = models.TextField(blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    error_code = models.CharField(
        max_length=USAGE_ERROR_MAX_LENGTH, blank=True, default=""
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ai_usage_log"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["workspace", "-created_at"], name="ai_usage_workspace_time"
            )
        ]
