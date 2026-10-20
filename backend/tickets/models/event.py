import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from tickets.constants.enums import EventType


class TicketEvent(models.Model):
    """Append-only history. Never holds message bodies or secrets."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="+"
    )
    ticket = models.ForeignKey(
        "tickets.Ticket", on_delete=models.CASCADE, related_name="events"
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    event_type = models.CharField(max_length=25, choices=EventType.choices)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "tickets_event"
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["ticket", "created_at"])]
