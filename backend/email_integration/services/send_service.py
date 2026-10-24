import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.exception.domain import ConflictException, NotFoundException
from email_integration import clients
from email_integration.clients.base import (
    GmailAuthError,
    GmailRejectedError,
    GmailTransientError,
)
from email_integration.constants import errors, messages
from email_integration.constants import settings as cfg
from email_integration.services import connection_service, mime_service
from tickets.constants.enums import (
    AuthorType,
    DeliveryStatus,
    EventType,
    MessageDirection,
    MessageVisibility,
)
from tickets.models import Ticket, TicketMessage
from tickets.services import ticket_service
from workspaces.constants import permissions
from workspaces.constants.roles import MembershipStatus, Role
from workspaces.constants.settings import INVITATION_EXPIRY
from workspaces.models import WorkspaceInvitation, WorkspaceMembership
from workspaces.services import access

logger = logging.getLogger(__name__)


class RetryableSendError(Exception):
    """Raised so the Celery task retries; the message stays QUEUED."""


def _thread_context(ticket: Ticket, mailbox_user) -> tuple[str, list[str], str]:
    """(gmail thread id in this mailbox, References chain, In-Reply-To) for a reply."""
    ids = list(
        ticket.messages.exclude(email_message_id="")
        .order_by("created_at", "id")
        .values_list("email_message_id", flat=True)
    )
    thread_id = (
        ticket.messages.filter(mailbox_user=mailbox_user)
        .exclude(email_thread_id="")
        .order_by("-created_at")
        .values_list("email_thread_id", flat=True)
        .first()
        or ""
    )
    return thread_id, ids, (ids[-1] if ids else "")


def _fail(message: TicketMessage, code: str) -> None:
    message.delivery_status = DeliveryStatus.FAILED
    message.delivery_error = code
    message.save(update_fields=["delivery_status", "delivery_error", "updated_at"])
    ticket_service.record_event(
        message.ticket,
        None,
        EventType.EMAIL_DELIVERY_FAILED,
        message_id=str(message.id),
        reason=code,
    )


def _deliver(
    message: TicketMessage, mailbox_user, *, subject: str, final_attempt: bool
) -> None:
    """Send one stored message from `mailbox_user`'s Gmail and record the outcome."""
    ticket = message.ticket
    connection = (
        connection_service.get_connection(mailbox_user) if mailbox_user else None
    )
    if connection is None or not connection.is_connected:
        _fail(message, errors.DELIVERY_NO_GMAIL)
        return
    thread_id, references, in_reply_to = _thread_context(ticket, mailbox_user)
    raw = mime_service.build_reply(
        from_name=mailbox_user.display_name or "",
        from_email=connection.mailbox_email,
        to_email=ticket.customer_email,
        subject=subject,
        body=message.body_text,
        in_reply_to=in_reply_to,
        references=references,
    )
    client = clients.get_gmail_client(connection)
    try:
        sent = client.send(raw, thread_id or None)
        actual = client.get_message(sent.id)  # Gmail may have replaced our Message-ID
    except GmailAuthError:
        connection_service.mark_reauth_required(connection)
        _fail(message, errors.DELIVERY_REAUTH)
        return
    except GmailRejectedError:
        _fail(message, errors.DELIVERY_REJECTED)
        return
    except GmailTransientError as exc:
        if final_attempt:
            _fail(message, errors.DELIVERY_UNAVAILABLE)
            return
        raise RetryableSendError from exc
    message.delivery_status = DeliveryStatus.SENT
    message.delivery_error = ""
    message.email_message_id = actual.headers.get("message-id", "")[:500]
    message.email_thread_id = sent.thread_id
    message.mailbox_user = mailbox_user
    message.sent_from_user = mailbox_user
    message.save()


def send_ticket_message(message_id, *, final_attempt: bool = False) -> None:
    """Email a QUEUED public reply from the agent's own mailbox. Idempotent."""
    with transaction.atomic():
        message = (
            # Lock only the message row: Postgres refuses FOR UPDATE on the nullable side of
            # the outer join that select_related("sent_from_user") creates.
            TicketMessage.objects.select_for_update(of=("self",))
            .select_related("ticket", "sent_from_user")
            .filter(pk=message_id)
            .first()
        )
        if (
            message is None
            or message.delivery_status != DeliveryStatus.QUEUED
            or message.visibility != MessageVisibility.PUBLIC
            or message.direction != MessageDirection.OUTBOUND
        ):
            return  # already sent, failed, or never an outgoing public message
        _deliver(
            message,
            message.sent_from_user,
            subject=mime_service.reply_subject(
                message.ticket.subject, message.ticket.number
            ),
            final_attempt=final_attempt,
        )


def send_portal_confirmation(ticket_id) -> None:
    """Confirm a portal ticket to the customer from the owner's mailbox (skipped when the
    owner has no connected Gmail). The mail is stored as a system message so the
    customer's reply to it matches the ticket by headers."""
    with transaction.atomic():
        ticket = (
            Ticket.objects.select_for_update()
            .filter(pk=ticket_id, confirmation_pending=True)
            .first()
        )
        if ticket is None:
            return
        ticket.confirmation_pending = False
        ticket.save(update_fields=["confirmation_pending", "updated_at"])
        owner = (
            WorkspaceMembership.objects.select_related("user")
            .filter(
                workspace_id=ticket.workspace_id,
                role=Role.OWNER,
                status=MembershipStatus.ACTIVE,
            )
            .first()
        )
        if owner is None:
            return
        connection = connection_service.get_connection(owner.user)
        if connection is None or not connection.is_connected:
            return
        portal_url = settings.FRONTEND_URL.rstrip("/") + cfg.PORTAL_PATH.format(
            slug=ticket.workspace.slug
        )
        body = (
            f"Hello{' ' + ticket.customer_name if ticket.customer_name else ''},\n\n"
            f"We received your request #{ticket.number}: {ticket.subject}\n"
            "Reply to this email to add more details. We will answer by email.\n\n"
            f"Need to send a new request? {portal_url}\n"
        )
        message = TicketMessage.objects.create(
            workspace_id=ticket.workspace_id,
            ticket=ticket,
            author_type=AuthorType.SYSTEM,
            visibility=MessageVisibility.PUBLIC,
            direction=MessageDirection.OUTBOUND,
            body_text=body,
            delivery_status=DeliveryStatus.QUEUED,
        )
        _deliver(
            message,
            owner.user,
            subject=f"We received your request #{ticket.number}: {ticket.subject}"[
                : cfg.SUBJECT_MAX_LENGTH
            ],
            final_attempt=True,
        )


def send_invitation_email(invitation_id) -> None:
    """Tell the invitee about an invitation, from the inviter's own Gmail. Best effort:
    a missing or broken Gmail connection just means no email (the invitation itself
    stays valid and shows up on the invitee's invitations page). Never raises, so the
    task cannot retry-loop and invitation creation is never affected."""
    invitation = (
        WorkspaceInvitation.objects.select_related("workspace", "invited_by")
        .filter(pk=invitation_id, notified_at__isnull=True)
        .first()
    )
    if invitation is None or not invitation.is_usable():
        return
    inviter = invitation.invited_by
    connection = connection_service.get_connection(inviter) if inviter else None
    if connection is None or not connection.is_connected:
        logger.info("Invitation %s email skipped: inviter has no Gmail", invitation.id)
        return
    inviter_name = inviter.display_name or inviter.email
    workspace_name = invitation.workspace.name
    link = settings.FRONTEND_URL.rstrip("/") + cfg.INVITATIONS_PATH
    body = (
        f'{inviter_name} invited you to join the workspace "{workspace_name}" '
        "on ResolveAI.\n\n"
        f"Sign in with this Google account and accept the invitation here:\n{link}\n\n"
        f"The invitation expires in {INVITATION_EXPIRY.days} days. If you were not expecting it, ignore this email.\n"
    )
    raw = mime_service.build_reply(
        from_name=inviter.display_name or "",
        from_email=connection.mailbox_email,
        to_email=invitation.email,
        subject=f"{inviter_name} invited you to {workspace_name} on ResolveAI",
        body=body,
    )
    try:
        clients.get_gmail_client(connection).send(raw, None)
    except GmailAuthError:
        connection_service.mark_reauth_required(connection)
        logger.warning(
            "Invitation %s email not sent: Gmail re-auth needed", invitation.id
        )
        return
    except GmailRejectedError, GmailTransientError:
        logger.warning("Invitation %s email not sent: Gmail error", invitation.id)
        return
    WorkspaceInvitation.objects.filter(pk=invitation.pk).update(
        notified_at=timezone.now()
    )


def resend(user, workspace_id, ticket_id, message_id) -> TicketMessage:
    """Put a FAILED reply back in the queue (same agent mailbox, so only its sender or the owner)."""
    membership = access.require_permission(
        user, workspace_id, permissions.TICKETS_MANAGE
    )
    message = TicketMessage.objects.filter(
        pk=message_id, ticket_id=ticket_id, workspace_id=workspace_id
    ).first()
    if message is None:
        raise NotFoundException(messages.MESSAGE_TICKET_NOT_FOUND)
    if (
        message.author_type != AuthorType.AGENT
        or message.delivery_status != DeliveryStatus.FAILED
    ):
        raise ConflictException(
            messages.MESSAGE_NOT_FAILED, error_code=errors.ERROR_NOT_FAILED
        )
    if message.sent_from_user_id != user.id and not membership.is_owner:
        raise NotFoundException(messages.MESSAGE_TICKET_NOT_FOUND)
    message.delivery_status = DeliveryStatus.QUEUED
    message.delivery_error = ""
    message.save(update_fields=["delivery_status", "delivery_error", "updated_at"])
    return message
