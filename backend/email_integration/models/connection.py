import uuid

from django.conf import settings
from django.db import models

from common.models import TimeStampModel
from email_integration.constants.enums import ConnectionStatus


class GmailConnection(TimeStampModel):
    """One per user, created or refreshed by Google sign-in. The refresh token is
    stored encrypted (common.crypto) and never leaves the server."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gmail_connection",
    )
    google_subject = models.CharField(max_length=64)
    mailbox_email = models.EmailField()
    encrypted_refresh_token = models.TextField(blank=True)
    granted_scopes = models.JSONField(default=list)
    status = models.CharField(
        max_length=20,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.NOT_CONNECTED,
    )
    connected_at = models.DateTimeField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    history_id = models.CharField(max_length=40, blank=True)
    watch_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "email_gmail_connection"
        indexes = [models.Index(fields=["mailbox_email"])]

    def __str__(self) -> str:
        return f"{self.mailbox_email} ({self.status})"

    @property
    def is_connected(self) -> bool:
        return self.status == ConnectionStatus.CONNECTED and bool(
            self.encrypted_refresh_token
        )
