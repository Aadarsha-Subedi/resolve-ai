"""Knowledge-base passages for a ticket or for one customer message of it."""

from accounts.models import User
from common.exception.domain import NotFoundException
from knowledge.services import context_service as knowledge_context
from tickets.constants import messages
from tickets.constants.enums import AuthorType, MessageVisibility
from tickets.models import TicketMessage
from tickets.services import ticket_service
from workspaces.services import access


def ticket_context(user: User, workspace_id, ticket_id, message_id=None):
    """Needs `tickets.view`. The query text is the chosen public customer message, or the
    ticket's subject and description. Internal notes and agent replies are never used, and a
    message id that is not a public customer message of this ticket looks like any other
    unknown id."""
    ticket = ticket_service.get_for_user(user, workspace_id, ticket_id)
    if message_id is None:
        text = f"{ticket.subject}\n{ticket.description}"
    else:
        message = TicketMessage.objects.filter(
            pk=message_id,
            ticket=ticket,
            workspace_id=workspace_id,
            author_type=AuthorType.CUSTOMER,
            visibility=MessageVisibility.PUBLIC,
        ).first()
        if message is None:
            raise NotFoundException(messages.MESSAGE_CONTEXT_MESSAGE_NOT_FOUND)
        text = message.body_text
    workspace = access.get_membership(user, workspace_id).workspace
    return knowledge_context.retrieve_context(user, workspace, text)
