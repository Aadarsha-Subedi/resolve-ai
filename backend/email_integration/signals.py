import logging

from allauth.account.signals import user_logged_in
from django.db import transaction
from django.dispatch import receiver

from email_integration.services import connection_service
from tickets.constants.enums import TicketSource
from tickets.services import hooks as ticket_hooks

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def record_gmail_grant(sender, request, user, **kwargs) -> None:
    # allauth's own signal (not Django's): it is the one that carries `sociallogin`.
    """Google sign-in also carries the Gmail grant: store it (encrypted) for this user."""
    sociallogin = kwargs.get("sociallogin")
    if sociallogin is None:
        return
    connection = connection_service.record_login_grant(user, sociallogin)
    if connection is not None and connection.is_connected:
        from email_integration.tasks import ensure_gmail_watch

        transaction.on_commit(lambda: ensure_gmail_watch.delay(str(connection.id)))


@receiver(ticket_hooks.ticket_signal)
def on_ticket_event(sender, ticket_id, action, metadata, **kwargs) -> None:
    from email_integration.tasks import send_portal_confirmation, send_ticket_message

    if action == ticket_hooks.ACTION_REPLY_ADDED and metadata.get("message_id"):
        transaction.on_commit(lambda: send_ticket_message.delay(metadata["message_id"]))
    elif (
        action == ticket_hooks.ACTION_CREATED
        and metadata.get("source") == TicketSource.PORTAL
    ):
        transaction.on_commit(lambda: send_portal_confirmation.delay(str(ticket_id)))
