from dataclasses import dataclass

from common.response.domain import BaseResponseData
from tickets.models import Ticket, TicketEvent, TicketMessage


@dataclass(frozen=True)
class TicketData(BaseResponseData):
    ticket: Ticket
    detail: bool = False

    def to_dict(self) -> dict:
        t = self.ticket
        data = {
            "id": str(t.id),
            "number": t.number,
            "subject": t.subject,
            "customer_name": t.customer_name,
            "customer_email": t.customer_email,
            "status": t.status,
            "priority": t.priority,
            "category": t.category,
            "created_via": t.created_via,
            "waiting_for_reply": t.waiting_for_reply,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
            "last_activity_at": t.last_activity_at.isoformat(),
        }
        if self.detail:
            data.update(
                {
                    "description": t.description,
                    "created_by": str(t.created_by_id) if t.created_by_id else None,
                    "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
                    "closed_at": t.closed_at.isoformat() if t.closed_at else None,
                    "last_customer_message_at": (
                        t.last_customer_message_at.isoformat()
                        if t.last_customer_message_at
                        else None
                    ),
                    "last_agent_reply_at": (
                        t.last_agent_reply_at.isoformat()
                        if t.last_agent_reply_at
                        else None
                    ),
                }
            )
        return data


@dataclass(frozen=True)
class MessageData(BaseResponseData):
    message: TicketMessage

    def to_dict(self) -> dict:
        m = self.message
        author = m.author_user
        return {
            "id": str(m.id),
            "author_type": m.author_type,
            "author": (
                {"id": str(author.id), "display_name": author.display_name}
                if author
                else None
            ),
            "visibility": m.visibility,
            "direction": m.direction,
            "body": m.body_text,
            "delivery_status": m.delivery_status or None,
            "created_at": m.created_at.isoformat(),
        }


@dataclass(frozen=True)
class EventData(BaseResponseData):
    event: TicketEvent

    def to_dict(self) -> dict:
        e = self.event
        return {
            "id": str(e.id),
            "event_type": e.event_type,
            "actor": str(e.actor_user_id) if e.actor_user_id else None,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "metadata": e.metadata,
            "created_at": e.created_at.isoformat(),
        }


@dataclass(frozen=True)
class DictData(BaseResponseData):
    payload: dict

    def to_dict(self) -> dict:
        return self.payload
