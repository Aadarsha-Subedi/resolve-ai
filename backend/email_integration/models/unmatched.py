import uuid

from django.conf import settings
from django.db import models

from common.models import TimeStampModel
from email_integration.constants.settings import (
    SENDER_NAME_MAX_LENGTH,
    SNIPPET_MAX_LENGTH,
    SUBJECT_MAX_LENGTH,
)


class UnmatchedEmail(TimeStampModel):
    """Mail from a known customer that could not be tied to a ticket by its headers.
    Only sender, subject and a short snippet are kept; the body is fetched again from
    Gmail if an agent attaches it to a ticket."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    mailbox_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="unmatched_emails",
    )
    gmail_message_id = models.CharField(max_length=64)
    email_message_id = models.CharField(max_length=500, blank=True)
    sender_email = models.EmailField()
    sender_name = models.CharField(max_length=SENDER_NAME_MAX_LENGTH, blank=True)
    subject = models.CharField(max_length=SUBJECT_MAX_LENGTH, blank=True)
    snippet = models.CharField(max_length=SNIPPET_MAX_LENGTH, blank=True)
    received_at = models.DateTimeField()

    class Meta:
        db_table = "email_unmatched"
        ordering = ["-received_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["mailbox_user", "gmail_message_id"],
                name="unique_unmatched_message_per_mailbox",
            )
        ]
