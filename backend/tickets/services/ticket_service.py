from datetime import date

from django.db import transaction
from django.db.models import Case, F, IntegerField, Q, QuerySet, Value, When
from django.utils import timezone

from accounts.models import User
from common.exception.domain import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from tickets import policies
from tickets.constants import errors, messages
from tickets.constants.enums import (
    AuthorType,
    DeliveryStatus,
    EventType,
    MessageDirection,
    MessageVisibility,
    TicketSource,
    TicketStatus,
)
from tickets.constants.settings import (
    DEFAULT_ORDERING,
    ORDERING_FIELDS,
    PRIORITY_RANK,
)
from tickets.models import Ticket, TicketEvent, TicketMessage
from tickets.services import hooks
from tickets.services.numbering import next_ticket_number
from workspaces.constants import permissions
from workspaces.services import access

_PROTECTED_FIELDS = (
    "subject",
    "description",
    "customer_name",
    "customer_email",
    "category",
    "priority",
)
_FIELD_EVENT = {
    "priority": EventType.PRIORITY_CHANGED,
    "category": EventType.CATEGORY_CHANGED,
}


def record_event(ticket: Ticket, actor, event_type, old=None, new=None, **metadata):
    return TicketEvent.objects.create(
        workspace_id=ticket.workspace_id,
        ticket=ticket,
        actor_user=actor,
        event_type=event_type,
        old_value=old,
        new_value=new,
        metadata=metadata,
    )


def create_ticket(
    workspace_id,
    *,
    subject: str,
    description: str,
    customer_email: str,
    customer_name: str = "",
    category: str,
    priority: str,
    source: str,
    actor: User | None = None,
    confirmation_pending: bool = False,
) -> Ticket:
    """The one place tickets are created (agent and portal). The customer's description
    becomes the first public message of the conversation."""
    now = timezone.now()
    with transaction.atomic():
        ticket = Ticket.objects.create(
            workspace_id=workspace_id,
            number=next_ticket_number(workspace_id),
            subject=subject,
            description=description,
            customer_name=customer_name,
            customer_email=customer_email,
            category=category,
            priority=priority,
            created_by=actor,
            created_via=source,
            last_customer_message_at=now,
            last_activity_at=now,
            confirmation_pending=confirmation_pending,
        )
        TicketMessage.objects.create(
            workspace_id=workspace_id,
            ticket=ticket,
            author_type=AuthorType.CUSTOMER,
            visibility=MessageVisibility.PUBLIC,
            direction=MessageDirection.INBOUND,
            body_text=description,
            delivery_status=DeliveryStatus.RECEIVED,
            external_sender_email=customer_email,
        )
        record_event(ticket, actor, EventType.CREATED, source=source)
    hooks.emit(ticket, actor, hooks.ACTION_CREATED, source=source)
    return ticket


def create_by_agent(user: User, workspace_id, data: dict) -> Ticket:
    access.require_permission(user, workspace_id, permissions.TICKETS_MANAGE)
    return create_ticket(
        workspace_id,
        subject=data["subject"],
        description=data["description"],
        customer_email=data["customer_email"],
        customer_name=data.get("customer_name", ""),
        category=data["category"],
        priority=data["priority"],
        source=TicketSource.AGENT,
        actor=user,
    )


def get_ticket(workspace_id, ticket_id) -> Ticket:
    ticket = Ticket.objects.filter(workspace_id=workspace_id, pk=ticket_id).first()
    if ticket is None:
        raise NotFoundException(messages.MESSAGE_TICKET_NOT_FOUND)
    return ticket


def get_for_user(user: User, workspace_id, ticket_id) -> Ticket:
    access.require_permission(user, workspace_id, permissions.TICKETS_VIEW)
    return get_ticket(workspace_id, ticket_id)


def update_ticket(user: User, workspace_id, ticket_id, changes: dict) -> Ticket:
    membership = access.require_permission(
        user, workspace_id, permissions.TICKETS_MANAGE
    )
    with transaction.atomic():
        ticket = (
            Ticket.objects.select_for_update()
            .filter(workspace_id=workspace_id, pk=ticket_id)
            .first()
        )
        if ticket is None:
            raise NotFoundException(messages.MESSAGE_TICKET_NOT_FOUND)
        policies.TicketPolicy.ensure_can_edit(membership, ticket)
        changed = []
        for field in _PROTECTED_FIELDS:
            if field in changes and changes[field] != getattr(ticket, field):
                old = getattr(ticket, field)
                setattr(ticket, field, changes[field])
                changed.append(field)
                if field in _FIELD_EVENT:
                    record_event(
                        ticket, user, _FIELD_EVENT[field], old=old, new=changes[field]
                    )
        details = [f for f in changed if f not in _FIELD_EVENT]
        if details:
            record_event(ticket, user, EventType.DETAILS_CHANGED, fields=details)
        if changed:
            ticket.last_activity_at = timezone.now()
            ticket.save()
    if changed:
        hooks.emit(ticket, user, hooks.ACTION_UPDATED, fields=changed)
    return ticket


def change_status(user: User, workspace_id, ticket_id, new_status: str) -> Ticket:
    membership = access.require_permission(
        user, workspace_id, permissions.TICKETS_MANAGE
    )
    now = timezone.now()
    with transaction.atomic():
        ticket = (
            Ticket.objects.select_for_update()
            .filter(workspace_id=workspace_id, pk=ticket_id)
            .first()
        )
        if ticket is None:
            raise NotFoundException(messages.MESSAGE_TICKET_NOT_FOUND)
        policies.TicketPolicy.ensure_can_change_status(membership, ticket, new_status)
        if ticket.status == new_status:
            raise ConflictException(
                messages.MESSAGE_STATUS_UNCHANGED, error_code=errors.ERROR_SAME_STATUS
            )
        old = ticket.status
        ticket.status = new_status
        if new_status == TicketStatus.RESOLVED:
            ticket.resolved_at = now
            ticket.closed_at = None
        elif new_status == TicketStatus.CLOSED:
            ticket.resolved_at = ticket.resolved_at or now
            ticket.closed_at = now
        else:  # open, in progress, pending: the ticket is active again
            ticket.resolved_at = None
            ticket.closed_at = None
        ticket.last_activity_at = now
        ticket.save()
        record_event(ticket, user, EventType.STATUS_CHANGED, old=old, new=new_status)
    hooks.emit(ticket, user, hooks.ACTION_STATUS_CHANGED, old=old, new=new_status)
    return ticket


def list_tickets(
    user: User,
    workspace_id,
    status=None,
    priority=None,
    category=None,
    created_from: date | None = None,
    created_to: date | None = None,
    q: str | None = None,
    waiting_for_reply: bool | None = None,
    ordering: str | None = None,
) -> QuerySet[Ticket]:
    """Workspace-scoped list. Search is a plain 'contains' on subject, customer email and name."""
    access.require_permission(user, workspace_id, permissions.TICKETS_VIEW)
    queryset = Ticket.objects.filter(workspace_id=workspace_id)
    if status:
        queryset = queryset.filter(status=status)
    if priority:
        queryset = queryset.filter(priority=priority)
    if category:
        queryset = queryset.filter(category=category)
    if created_from:
        queryset = queryset.filter(created_at__date__gte=created_from)
    if created_to:
        queryset = queryset.filter(created_at__date__lte=created_to)
    if q:
        queryset = queryset.filter(
            Q(subject__icontains=q)
            | Q(customer_email__icontains=q)
            | Q(customer_name__icontains=q)
        )
    if waiting_for_reply is not None:
        waiting = Q(last_customer_message_at__isnull=False) & (
            Q(last_agent_reply_at__isnull=True)
            | Q(last_customer_message_at__gt=F("last_agent_reply_at"))
        )
        queryset = (
            queryset.filter(waiting) if waiting_for_reply else queryset.exclude(waiting)
        )
    ordering = ordering or DEFAULT_ORDERING
    field = ordering.lstrip("-")
    if field not in ORDERING_FIELDS:
        raise BadRequestException(
            f"Order by one of: {', '.join(sorted(ORDERING_FIELDS))}."
        )
    if (
        field == "priority"
    ):  # alphabetical order would put "high" before "low" and "urgent" last
        queryset = queryset.annotate(
            priority_rank=Case(
                *[
                    When(priority=name, then=Value(rank))
                    for name, rank in PRIORITY_RANK.items()
                ],
                output_field=IntegerField(),
            )
        )
        field = "priority_rank"
    prefix = "-" if ordering.startswith("-") else ""
    return queryset.order_by(prefix + field, "-number")


def list_events(user: User, workspace_id, ticket_id) -> QuerySet[TicketEvent]:
    get_for_user(user, workspace_id, ticket_id)
    return TicketEvent.objects.filter(ticket_id=ticket_id, workspace_id=workspace_id)
