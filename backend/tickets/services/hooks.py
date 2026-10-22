"""Audit extension point (feature 2 subscribes to `ticket_event_signal` when built).
Metadata never carries message bodies or customer email addresses."""

from django.dispatch import Signal

SENDER = "tickets"
ticket_signal = Signal()  # kwargs: workspace_id, ticket_id, actor, action, metadata

ACTION_CREATED = "ticket.created"
ACTION_UPDATED = "ticket.updated"
ACTION_STATUS_CHANGED = "ticket.status_changed"
ACTION_ASSIGNEE_CHANGED = "ticket.assignee_changed"
ACTION_REPLY_ADDED = "ticket.reply_added"
ACTION_NOTE_ADDED = "ticket.note_added"


def emit(ticket, actor, action: str, **metadata) -> None:
    ticket_signal.send(
        sender=SENDER,
        workspace_id=ticket.workspace_id,
        ticket_id=ticket.id,
        actor=actor,
        action=action,
        metadata=metadata,
    )
