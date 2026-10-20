import uuid

from django.conf import settings
from django.db import models

from common.models import TimeStampModel
from tickets.constants.enums import (
    AuthorType,
    DeliveryStatus,
    MessageDirection,
    MessageVisibility,
)


class TicketMessage(TimeStampModel):
    """A public message or an internal note. Rows are never edited or deleted by the API."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="+"
    )
    ticket = models.ForeignKey(
        "tickets.Ticket", on_delete=models.CASCADE, related_name="messages"
    )
    author_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    author_type = models.CharField(max_length=10, choices=AuthorType.choices)
    visibility = models.CharField(max_length=10, choices=MessageVisibility.choices)
    direction = models.CharField(max_length=10, choices=MessageDirection.choices)
    body_text = models.TextField()
    delivery_status = models.CharField(
        max_length=10, choices=DeliveryStatus.choices, blank=True
    )
    # Email correlation fields, filled by feature 6 (Gmail). Email is never the source of truth.
    email_message_id = models.CharField(max_length=500, blank=True)
    email_thread_id = models.CharField(max_length=200, blank=True)
    in_reply_to = models.CharField(max_length=500, blank=True)
    references_header = models.TextField(blank=True)
    # Whose connected mailbox the email passed through (inbound and outbound).
    mailbox_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    delivery_error = models.CharField(max_length=40, blank=True)
    sent_from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    external_sender_email = models.EmailField(blank=True)

    class Meta:
        db_table = "tickets_message"
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["ticket", "created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "email_message_id"],
                condition=~models.Q(email_message_id=""),
                name="unique_email_message_per_workspace",
            )
        ]
