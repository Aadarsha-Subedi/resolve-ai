import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from audit.constants import settings as cfg


class AuditEvent(models.Model):
    """Append-only record of a sensitive action. The API only reads; rows are never updated.
    It lives and dies with its workspace (purged together); account-level rows have none."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Display name at the time, so the log still reads well after the account is gone.
    actor_name = models.CharField(max_length=cfg.ACTOR_NAME_MAX_LENGTH, blank=True)
    action = models.CharField(max_length=cfg.ACTION_MAX_LENGTH)
    target_type = models.CharField(max_length=cfg.TARGET_TYPE_MAX_LENGTH, blank=True)
    target_id = models.CharField(max_length=cfg.TARGET_ID_MAX_LENGTH, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "audit_event"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["workspace", "-created_at"]),
            models.Index(fields=["workspace", "action", "-created_at"]),
            models.Index(fields=["workspace", "actor_user", "-created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Audit events are append-only.")
        super().save(*args, **kwargs)
