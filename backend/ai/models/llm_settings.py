import uuid

from django.conf import settings
from django.db import models

from ai.constants.settings import (
    KEY_LAST4_LENGTH,
    MODE_MAX_LENGTH,
    MODE_OWN_KEY,
    MODE_RESOLVE_AI,
    MODEL_MAX_LENGTH,
    PROVIDER_MAX_LENGTH,
)
from common.llm.constants import DEFAULT_MODELS, PROVIDER_GEMINI


class UserWorkspaceLLMSettings(models.Model):
    """Where one user's AI calls go inside one workspace: our Gemini key or their own key.

    The key is stored encrypted (see `ai.services.key_vault`) and is never returned.
    No row means the defaults: Resolve AI mode on the default model.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="+"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    mode = models.CharField(
        max_length=MODE_MAX_LENGTH,
        choices=[(MODE_RESOLVE_AI, "Resolve AI"), (MODE_OWN_KEY, "Own key")],
        default=MODE_RESOLVE_AI,
    )
    resolve_ai_model = models.CharField(
        max_length=MODEL_MAX_LENGTH, default=DEFAULT_MODELS[PROVIDER_GEMINI]
    )
    # Which saved key answers in own-key mode ("" when there is none).
    active_provider = models.CharField(max_length=PROVIDER_MAX_LENGTH, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user"], name="ai_llm_settings_ws_user_uniq"
            )
        ]

    @property
    def uses_own_key(self) -> bool:
        return self.mode == MODE_OWN_KEY


class UserWorkspaceLLMKey(models.Model):
    """One saved API key of one user for one provider in one workspace (at most one per
    provider). Stored encrypted (see `ai.services.key_vault`) and never returned."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="+"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    provider = models.CharField(max_length=PROVIDER_MAX_LENGTH)
    model = models.CharField(max_length=MODEL_MAX_LENGTH)
    key_encrypted = models.TextField()
    key_last4 = models.CharField(max_length=KEY_LAST4_LENGTH)
    checked_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user", "provider"],
                name="ai_llm_key_ws_user_provider_uniq",
            )
        ]
        ordering = ["created_at", "id"]
