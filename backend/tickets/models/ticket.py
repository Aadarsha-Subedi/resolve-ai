import uuid

from django.conf import settings
from django.db import models

from common.models import TimeStampModel
from tickets.constants.enums import (
    TicketCategory,
    TicketPriority,
    TicketSource,
    TicketStatus,
)
from tickets.constants.settings import (
    CUSTOMER_NAME_MAX_LENGTH,
    DEFAULT_CATEGORY,
    DEFAULT_PRIORITY,
    SUBJECT_MAX_LENGTH,
)


class Ticket(TimeStampModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="tickets"
    )
    number = models.PositiveIntegerField()
    subject = models.CharField(max_length=SUBJECT_MAX_LENGTH)
    description = models.TextField()
    customer_name = models.CharField(max_length=CUSTOMER_NAME_MAX_LENGTH, blank=True)
    customer_email = models.EmailField()
    status = models.CharField(
        max_length=12, choices=TicketStatus.choices, default=TicketStatus.OPEN
    )
    priority = models.CharField(
        max_length=10, choices=TicketPriority.choices, default=DEFAULT_PRIORITY
    )
    category = models.CharField(
        max_length=20, choices=TicketCategory.choices, default=DEFAULT_CATEGORY
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_via = models.CharField(max_length=10, choices=TicketSource.choices)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    last_customer_message_at = models.DateTimeField(null=True, blank=True)
    last_agent_reply_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField()
    # Portal tickets need a confirmation email; feature 6 sends it and clears the flag.
    confirmation_pending = models.BooleanField(default=False)

    class Meta:
        db_table = "tickets_ticket"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "number"],
                name="unique_ticket_number_per_workspace",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "status", "-updated_at"]),
            models.Index(fields=["workspace", "priority", "-created_at"]),
            models.Index(fields=["workspace", "customer_email"]),
            models.Index(fields=["workspace", "-last_activity_at"]),
            models.Index(fields=["workspace", "resolved_at"]),
            models.Index(fields=["workspace", "created_at"]),
        ]

    @property
    def waiting_for_reply(self) -> bool:
        """The last public message came from the customer, so the ticket awaits an agent."""
        if self.last_customer_message_at is None:
            return False
        return (
            self.last_agent_reply_at is None
            or self.last_customer_message_at > self.last_agent_reply_at
        )
