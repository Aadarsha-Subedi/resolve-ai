"""One call for the ticket page: ticket, conversation, history and what the viewer may do.

Other apps add their own small block (for example the viewer's Gmail status) by registering
a provider, so `tickets` never imports them."""

from collections.abc import Callable
from dataclasses import dataclass

from accounts.models import User
from tickets.models import Ticket, TicketEvent, TicketMessage
from tickets.services import message_service, ticket_service
from workspaces.constants.permissions import ROLE_PERMISSIONS
from workspaces.services import access

DEFAULT_LIMIT = 50

OverviewExtra = Callable[[User, Ticket], dict]
_extras: dict[str, OverviewExtra] = {}


def register_extra(key: str, provider: OverviewExtra) -> None:
    _extras[key] = provider


@dataclass(frozen=True)
class Overview:
    ticket: Ticket
    role: str
    permissions: list[str]
    messages: list[TicketMessage]
    messages_total: int
    events: list[TicketEvent]
    events_total: int
    extras: dict


def _newest(queryset, limit: int) -> tuple[list, int]:
    """The newest `limit` rows in chronological order, and the total count."""
    total = queryset.count()
    rows = list(queryset.order_by("-created_at", "-id")[:limit])
    rows.reverse()
    return rows, total


def build(
    user: User,
    workspace_id,
    ticket_id,
    messages_limit: int = DEFAULT_LIMIT,
    events_limit: int = DEFAULT_LIMIT,
) -> Overview:
    ticket = ticket_service.get_for_user(
        user, workspace_id, ticket_id
    )  # 404 / 403 as usual
    membership = access.get_membership(user, workspace_id)
    messages, messages_total = _newest(
        message_service.list_messages(user, workspace_id, ticket_id), messages_limit
    )
    events, events_total = _newest(
        ticket_service.list_events(user, workspace_id, ticket_id), events_limit
    )
    return Overview(
        ticket=ticket,
        role=membership.role,
        permissions=sorted(ROLE_PERMISSIONS.get(membership.role, ())),
        messages=messages,
        messages_total=messages_total,
        events=events,
        events_total=events_total,
        extras={key: provider(user, ticket) for key, provider in _extras.items()},
    )
