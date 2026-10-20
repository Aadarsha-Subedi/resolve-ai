from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from accounts.models import User
from common.exception.domain import NotFoundException
from tickets import policies
from tickets.constants import messages
from tickets.constants.enums import (
    AuthorType,
    DeliveryStatus,
    EventType,
    MessageDirection,
    MessageVisibility,
)
from tickets.models import Ticket, TicketMessage
from tickets.services import hooks, ticket_service
from workspaces.constants import permissions
from workspaces.services import access


def list_messages(user: User, workspace_id, ticket_id) -> QuerySet[TicketMessage]:
    """Everything, internal notes included: this is the agent view. No customer-facing
    endpoint exists for ticket history."""
    ticket_service.get_for_user(user, workspace_id, ticket_id)
    return TicketMessage.objects.select_related("author_user").filter(
        ticket_id=ticket_id, workspace_id=workspace_id
    )


def add_message(
    user: User, workspace_id, ticket_id, body: str, visibility: str
) -> TicketMessage:
    access.require_permission(user, workspace_id, permissions.TICKETS_MANAGE)
    public = visibility == MessageVisibility.PUBLIC
    now = timezone.now()
    with transaction.atomic():
        ticket = (
            Ticket.objects.select_for_update()
            .filter(workspace_id=workspace_id, pk=ticket_id)
            .first()
        )
        if ticket is None:
            raise NotFoundException(messages.MESSAGE_TICKET_NOT_FOUND)
        if public:
            policies.TicketPolicy.ensure_can_reply(ticket)
        message = TicketMessage.objects.create(
            workspace_id=workspace_id,
            ticket=ticket,
            author_user=user,
            author_type=AuthorType.AGENT,
            visibility=visibility,
            direction=MessageDirection.OUTBOUND
            if public
            else MessageDirection.INTERNAL,
            body_text=body,
            # A public reply is stored first, then feature 6 emails it from the agent's mailbox.
            delivery_status=DeliveryStatus.QUEUED if public else "",
            sent_from_user=user if public else None,
        )
        ticket.last_activity_at = now
        if public:
            ticket.last_agent_reply_at = now
        ticket.save(
            update_fields=["last_activity_at", "last_agent_reply_at", "updated_at"]
        )
        ticket_service.record_event(
            ticket,
            user,
            EventType.PUBLIC_REPLY_ADDED if public else EventType.INTERNAL_NOTE_ADDED,
            message_id=str(message.id),  # the body itself is never copied into history
        )
    hooks.emit(
        ticket,
        user,
        hooks.ACTION_REPLY_ADDED if public else hooks.ACTION_NOTE_ADDED,
        message_id=str(message.id),
    )
    return message
