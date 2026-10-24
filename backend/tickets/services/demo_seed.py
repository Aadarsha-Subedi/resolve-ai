"""Writes the demo workspace's sample tickets (tickets.constants.demo) straight to the
models, with timestamps in the past so the queue, the dashboard and each ticket's history
look like a desk that has been running for a few weeks.

The rows are written directly rather than through ticket_service so nothing is emailed,
no confirmation is queued and the audit log is not filled with seeding noise.
"""

from datetime import timedelta

from django.utils import timezone

from accounts.models import User
from tickets.constants.demo import CUSTOMER, DEMO_TICKETS, NOTE, REPLY
from tickets.constants.enums import (
    AuthorType,
    DeliveryStatus,
    EventType,
    MessageDirection,
    MessageVisibility,
    TicketStatus,
)
from tickets.models import Ticket, TicketEvent, TicketMessage
from workspaces.models import Workspace

_SETTLED = (TicketStatus.RESOLVED, TicketStatus.CLOSED)


def _message(workspace, ticket, owner, kind, body, at) -> TicketMessage:
    if kind == CUSTOMER:
        fields = {
            "author_type": AuthorType.CUSTOMER,
            "visibility": MessageVisibility.PUBLIC,
            "direction": MessageDirection.INBOUND,
            "delivery_status": DeliveryStatus.RECEIVED,
            "external_sender_email": ticket.customer_email,
        }
    elif kind == REPLY:
        fields = {
            "author_type": AuthorType.AGENT,
            "author_user": owner,
            "visibility": MessageVisibility.PUBLIC,
            "direction": MessageDirection.OUTBOUND,
            "delivery_status": DeliveryStatus.SENT,
            "sent_from_user": owner,
        }
    else:
        fields = {
            "author_type": AuthorType.AGENT,
            "author_user": owner,
            "visibility": MessageVisibility.INTERNAL,
            "direction": MessageDirection.INTERNAL,
            "delivery_status": "",
        }
    return TicketMessage(
        workspace=workspace,
        ticket=ticket,
        body_text=body,
        created_at=at,
        updated_at=at,
        **fields,
    )


def _event(workspace, ticket, actor, event_type, at, old=None, new=None, **metadata):
    return TicketEvent(
        workspace=workspace,
        ticket=ticket,
        actor_user=actor,
        event_type=event_type,
        old_value=old,
        new_value=new,
        metadata=metadata,
        created_at=at,
    )


def seed(workspace: Workspace, owner: User) -> None:
    now = timezone.now()
    ago = lambda hours: now - timedelta(hours=hours)  # noqa: E731
    # Oldest first, so ticket numbers rise with age like a real queue.
    specs = sorted(DEMO_TICKETS, key=lambda s: -s["thread"][0][0])
    messages: list[TicketMessage] = []
    events: list[TicketEvent] = []
    for number, spec in enumerate(specs, start=1):
        thread = spec["thread"]
        opened, last = ago(thread[0][0]), ago(thread[-1][0])
        customer_times = [ago(h) for h, kind, _ in thread if kind == CUSTOMER]
        reply_times = [ago(h) for h, kind, _ in thread if kind == REPLY]
        status = spec["status"]
        settled_at = last + timedelta(minutes=20)
        ticket = Ticket.objects.create(
            workspace=workspace,
            number=number,
            subject=spec["subject"],
            description=thread[0][2],
            customer_name=spec["customer_name"],
            customer_email=spec["customer_email"],
            status=status,
            priority=spec["priority"],
            category=spec["category"],
            assignee=owner if spec["assigned"] else None,
            created_via=spec["source"],
            resolved_at=settled_at if status in _SETTLED else None,
            closed_at=settled_at if status == TicketStatus.CLOSED else None,
            last_customer_message_at=max(customer_times),
            last_agent_reply_at=max(reply_times) if reply_times else None,
            last_activity_at=settled_at if status in _SETTLED else last,
        )
        # auto_now_add ignores a value given to create(), so backdate afterwards.
        Ticket.objects.filter(pk=ticket.pk).update(created_at=opened, updated_at=last)

        events.append(
            _event(
                workspace, ticket, None, EventType.CREATED, opened, source=spec["source"]
            )
        )
        if spec["assigned"]:
            events.append(
                _event(
                    workspace,
                    ticket,
                    owner,
                    EventType.ASSIGNEE_CHANGED,
                    opened + timedelta(minutes=5),
                    new={"id": str(owner.id), "display_name": owner.display_name},
                )
            )
        for index, (hours, kind, body) in enumerate(thread):
            at = ago(hours)
            message = _message(workspace, ticket, owner, kind, body, at)
            messages.append(message)
            if index == 0:
                continue
            event_type = {
                CUSTOMER: EventType.CUSTOMER_REPLY_RECEIVED,
                REPLY: EventType.PUBLIC_REPLY_ADDED,
                NOTE: EventType.INTERNAL_NOTE_ADDED,
            }[kind]
            actor = None if kind == CUSTOMER else owner
            events.append(
                _event(
                    workspace,
                    ticket,
                    actor,
                    event_type,
                    at,
                    message_id=str(message.id),
                )
            )
        if status != TicketStatus.OPEN:
            status_at = settled_at if status in _SETTLED else opened + timedelta(hours=1)
            events.append(
                _event(
                    workspace,
                    ticket,
                    owner,
                    EventType.STATUS_CHANGED,
                    status_at,
                    old=TicketStatus.OPEN.value,
                    new=status,
                )
            )

    TicketMessage.objects.bulk_create(messages)
    # auto_now_add overrides created_at in bulk_create too (TicketEvent has no auto_now_add).
    for message in messages:
        TicketMessage.objects.filter(pk=message.pk).update(
            created_at=message.created_at, updated_at=message.created_at
        )
    TicketEvent.objects.bulk_create(events)
    Workspace.all_objects.filter(pk=workspace.pk).update(last_ticket_number=len(specs))


def clear(workspace: Workspace) -> None:
    """Every ticket in the workspace (messages and events cascade) and its numbering."""
    Ticket.objects.filter(workspace=workspace).delete()
    Workspace.all_objects.filter(pk=workspace.pk).update(last_ticket_number=0)
