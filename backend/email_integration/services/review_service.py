from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from accounts.models import User
from common.exception.domain import ConflictException, NotFoundException
from email_integration import clients
from email_integration.clients.base import GmailAuthError, GmailError
from email_integration.constants import errors, messages
from email_integration.models import UnmatchedEmail
from email_integration.services import connection_service, inbound_service
from tickets.models import Ticket
from workspaces.constants import permissions
from workspaces.services import access


def list_review(user: User) -> QuerySet[UnmatchedEmail]:
    return UnmatchedEmail.objects.filter(mailbox_user=user)


def _get(user: User, review_id) -> UnmatchedEmail:
    item = UnmatchedEmail.objects.filter(mailbox_user=user, pk=review_id).first()
    if item is None:
        raise NotFoundException(messages.MESSAGE_REVIEW_NOT_FOUND)
    return item


def dismiss(user: User, review_id) -> None:
    _get(user, review_id).delete()


def attach_to_ticket(user: User, review_id, workspace_id, ticket_id) -> Ticket:
    """The agent decides which ticket the mail belongs to. The body is fetched from Gmail
    again now (it was never stored), then the review item is removed."""
    access.require_permission(user, workspace_id, permissions.TICKETS_MANAGE)
    ticket = Ticket.objects.filter(workspace_id=workspace_id, pk=ticket_id).first()
    if ticket is None:
        raise NotFoundException(messages.MESSAGE_TICKET_NOT_FOUND)
    item = _get(user, review_id)
    connection = connection_service.get_connection(user)
    if connection is None or not connection.is_connected:
        raise ConflictException(
            messages.MESSAGE_NOT_CONNECTED, error_code=errors.ERROR_NOT_CONNECTED
        )
    try:
        gmail_message = clients.get_gmail_client(connection).get_message(
            item.gmail_message_id
        )
    except GmailAuthError:
        connection_service.mark_reauth_required(connection)
        raise ConflictException(
            messages.MESSAGE_REAUTH_REQUIRED, error_code=errors.ERROR_REAUTH_REQUIRED
        ) from None
    except GmailError:
        raise ConflictException(
            messages.MESSAGE_GMAIL_UNAVAILABLE,
            error_code=errors.ERROR_GMAIL_UNAVAILABLE,
        ) from None
    with transaction.atomic():
        try:
            stored = inbound_service._store_customer_reply(
                connection, ticket, gmail_message, item.sender_email
            )
        except IntegrityError:
            stored = False
        item.delete()
    if not stored:  # the same mail was already on the ticket
        return ticket
    return ticket


def purge_old_items() -> int:
    cutoff = timezone.now() - timedelta(days=settings.GMAIL_REVIEW_RETENTION_DAYS)
    deleted, _ = UnmatchedEmail.objects.filter(received_at__lt=cutoff).delete()
    return deleted
