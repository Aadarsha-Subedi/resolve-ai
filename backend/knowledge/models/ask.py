import uuid

from django.conf import settings
from django.db import models

from knowledge.constants.settings import ASK_TITLE_MAX_LENGTH


class AskConversation(models.Model):
    """One chat on the Ask page. Private to the user who started it, inside one workspace."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="+"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    title = models.CharField(max_length=ASK_TITLE_MAX_LENGTH)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_ask_conversation"
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(
                fields=["workspace", "user", "-updated_at"],
                name="knowledge_ask_conv_owner",
            )
        ]


class AskTurn(models.Model):
    """One question and what came back, stored as it was shown (the passages included),
    so reopening a chat never changes what the user saw."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    conversation = models.ForeignKey(
        AskConversation, on_delete=models.CASCADE, related_name="turns"
    )
    question = models.TextField()
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "knowledge_ask_turn"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(
                fields=["conversation", "created_at"], name="knowledge_ask_turn_conv"
            )
        ]
