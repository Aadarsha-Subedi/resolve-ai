"""Response shapes. Only ticket fields and event types are exposed: never message text,
customer email addresses or event metadata."""

from dataclasses import dataclass

from audit.constants.dashboard import ACTIVITY_SOURCE_TICKET
from audit.services import dashboard_metrics as metrics
from common.response.domain import BaseResponseData
from tickets.models import Ticket, TicketEvent


@dataclass(frozen=True)
class DashboardData(BaseResponseData):
    payload: dict

    def to_dict(self) -> dict:
        return self.payload


def _ticket_ref(ticket: Ticket) -> dict:
    return {
        "id": str(ticket.id),
        "number": ticket.number,
        "subject": ticket.subject,
    }


def recent_item(ticket: Ticket) -> dict:
    return {
        **_ticket_ref(ticket),
        "customer_name": ticket.customer_name,
        "status": ticket.status,
        "priority": ticket.priority,
        "category": ticket.category,
        "waiting_for_reply": ticket.waiting_for_reply,
        "created_at": ticket.created_at.isoformat(),
        "last_activity_at": ticket.last_activity_at.isoformat(),
    }


def waiting_item(ticket: Ticket) -> dict:
    return {
        **_ticket_ref(ticket),
        "customer_name": ticket.customer_name,
        "status": ticket.status,
        "priority": ticket.priority,
        "waiting_since": ticket.last_customer_message_at.isoformat(),
    }


def activity_item(event: TicketEvent) -> dict:
    actor = event.actor_user
    changed = metrics.is_change_event(event.event_type)
    return {
        "id": str(event.id),
        "source": ACTIVITY_SOURCE_TICKET,
        "event_type": event.event_type,
        "ticket": _ticket_ref(event.ticket),
        "actor": {"id": str(actor.pk), "name": actor.display_name} if actor else None,
        "old_value": event.old_value if changed else None,
        "new_value": event.new_value if changed else None,
        "created_at": event.created_at.isoformat(),
    }
