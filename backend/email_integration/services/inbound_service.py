"""Reading new mail from an agent's Gmail and tying it to tickets.

Only mail that belongs to tickets is stored. Anything else in the mailbox is ignored, so a
personal inbox is never copied: no backfill, no unrelated mail, nothing kept unless the
message answers one of our mails (matched by headers) or comes from a known customer."""

import logging
from dataclasses import dataclass, field

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from common.email.utils import canonical_email_key
from email_integration import clients
from email_integration.clients.base import (
    GmailAuthError,
    GmailMessage,
    GmailRejectedError,
)
from email_integration.constants import settings as cfg
from email_integration.constants.enums import SyncOutcome
from email_integration.models import GmailConnection, UnmatchedEmail
from email_integration.services import connection_service, parsing
from tickets.constants.enums import (
    AuthorType,
    DeliveryStatus,
    EventType,
    MessageDirection,
    MessageVisibility,
)
from tickets.models import Ticket, TicketMessage
from tickets.services import ticket_service
from workspaces.constants.roles import MembershipStatus
from workspaces.models import WorkspaceMembership

logger = logging.getLogger(__name__)


@dataclass
class SyncReport:
    matched: int = 0
    review: int = 0
    duplicate: int = 0
    ignored: int = 0
    reauth_required: bool = False
    outcomes: list[str] = field(default_factory=list)

    def add(self, outcome: SyncOutcome) -> None:
        self.outcomes.append(outcome)
        setattr(self, outcome.value, getattr(self, outcome.value) + 1)


def _member_workspace_ids(connection: GmailConnection) -> list:
    return list(
        WorkspaceMembership.objects.filter(
            user=connection.user,
            status=MembershipStatus.ACTIVE,
            workspace__is_deleted=False,
            workspace__is_demo=False,  # sample tickets never match real mail
        ).values_list("workspace_id", flat=True)
    )


def _find_ticket_by_headers(workspace_ids, referenced: list[str]) -> Ticket | None:
    if not referenced:
        return None
    anchor = (
        TicketMessage.objects.select_related("ticket")
        .filter(workspace_id__in=workspace_ids, email_message_id__in=referenced)
        .order_by("-created_at")
        .first()
    )
    return anchor.ticket if anchor else None


def _is_known_customer(workspace_ids, sender_key: str, sender_email: str) -> bool:
    """A ticket in one of the agent's workspaces was opened by this address."""
    candidates = Ticket.objects.filter(workspace_id__in=workspace_ids).filter(
        Q(customer_email=sender_email) | Q(customer_email__iexact=sender_email)
    )
    if candidates.exists():
        return True
    # Gmail spellings (dots, +tags) of the same mailbox.
    domain = sender_key.rpartition("@")[2]
    same_domain = Ticket.objects.filter(
        workspace_id__in=workspace_ids, customer_email__iendswith=f"@{domain}"
    ).values_list("customer_email", flat=True)[:500]
    return any(canonical_email_key(e) == sender_key for e in same_domain)


def _store_customer_reply(
    connection: GmailConnection,
    ticket: Ticket,
    gmail_message: GmailMessage,
    sender_email: str,
) -> bool:
    """Create the inbound ticket message. False if it already exists (duplicate delivery)."""
    email_message_id = (
        gmail_message.headers.get("message-id") or f"gmail:{gmail_message.id}"
    )[:500]
    now = timezone.now()
    try:
        with transaction.atomic():
            TicketMessage.objects.create(
                workspace_id=ticket.workspace_id,
                ticket=ticket,
                author_type=AuthorType.CUSTOMER,
                visibility=MessageVisibility.PUBLIC,
                direction=MessageDirection.INBOUND,
                body_text=parsing.strip_quoted_reply(gmail_message.body_text)
                or gmail_message.snippet,
                delivery_status=DeliveryStatus.RECEIVED,
                email_message_id=email_message_id,
                email_thread_id=gmail_message.thread_id,
                in_reply_to=gmail_message.headers.get("in-reply-to", "")[:500],
                references_header=gmail_message.headers.get("references", ""),
                mailbox_user=connection.user,
                external_sender_email=sender_email,
            )
            Ticket.objects.filter(pk=ticket.pk).update(
                last_customer_message_at=now, last_activity_at=now, updated_at=now
            )
            ticket_service.record_event(
                ticket, None, EventType.CUSTOMER_REPLY_RECEIVED, source="email"
            )
    except IntegrityError:
        return False
    return True


def _store_for_review(
    connection: GmailConnection, gmail_message: GmailMessage, name, email
) -> bool:
    _, created = UnmatchedEmail.objects.get_or_create(
        mailbox_user=connection.user,
        gmail_message_id=gmail_message.id,
        defaults={
            "email_message_id": gmail_message.headers.get("message-id", "")[:500],
            "sender_email": email,
            "sender_name": name[: cfg.SENDER_NAME_MAX_LENGTH],
            "subject": parsing.clean_header(gmail_message.headers.get("subject", ""))[
                : cfg.SUBJECT_MAX_LENGTH
            ],
            "snippet": gmail_message.snippet[: cfg.SNIPPET_MAX_LENGTH],
            "received_at": gmail_message.received_at,
        },
    )
    if created:
        from django.conf import settings

        keep = list(
            UnmatchedEmail.objects.filter(mailbox_user=connection.user)
            .order_by("-received_at", "id")
            .values_list("pk", flat=True)[: settings.GMAIL_REVIEW_MAX_PER_USER]
        )
        UnmatchedEmail.objects.filter(mailbox_user=connection.user).exclude(
            pk__in=keep
        ).delete()
    return created


def process_message(
    connection: GmailConnection, gmail_message: GmailMessage
) -> SyncOutcome:
    if "INBOX" not in gmail_message.label_ids or "SENT" in gmail_message.label_ids:
        return SyncOutcome.IGNORED
    name, sender = parsing.parse_sender(gmail_message.headers.get("from", ""))
    if not sender or sender == connection.mailbox_email.lower():
        return SyncOutcome.IGNORED
    workspace_ids = _member_workspace_ids(connection)
    if not workspace_ids:
        return SyncOutcome.IGNORED
    email_message_id = (
        gmail_message.headers.get("message-id") or f"gmail:{gmail_message.id}"
    )
    if TicketMessage.objects.filter(
        workspace_id__in=workspace_ids, email_message_id=email_message_id[:500]
    ).exists():
        return SyncOutcome.DUPLICATE
    if UnmatchedEmail.objects.filter(
        mailbox_user=connection.user, gmail_message_id=gmail_message.id
    ).exists():
        return SyncOutcome.DUPLICATE

    sender_key = canonical_email_key(sender)
    referenced = parsing.message_ids(
        gmail_message.headers.get("in-reply-to", ""),
        gmail_message.headers.get("references", ""),
    )
    ticket = _find_ticket_by_headers(workspace_ids, referenced)
    # A header match alone is not enough: the sender must be the ticket's customer, otherwise
    # anyone who learned a Message-ID (a forward, a leak) could write into the ticket.
    if ticket is not None and canonical_email_key(ticket.customer_email) == sender_key:
        stored = _store_customer_reply(connection, ticket, gmail_message, sender)
        return SyncOutcome.MATCHED if stored else SyncOutcome.DUPLICATE
    if _is_known_customer(workspace_ids, sender_key, sender):
        created = _store_for_review(connection, gmail_message, name, sender)
        return SyncOutcome.REVIEW if created else SyncOutcome.DUPLICATE
    return SyncOutcome.IGNORED


def _process_ids(connection: GmailConnection, client, ids: list[str]) -> SyncReport:
    report = SyncReport()
    for gmail_id in ids:
        report.add(process_message(connection, client.get_message(gmail_id)))
    return report


def manual_sync(connection: GmailConnection) -> SyncReport:
    """ "Sync latest mails": look at the newest messages only (capped), never the whole mailbox."""
    from django.conf import settings

    client = clients.get_gmail_client(connection)
    try:
        ids = client.list_inbox(settings.GMAIL_MANUAL_SYNC_LIMIT)
        report = _process_ids(connection, client, ids)
        if not connection.history_id:
            connection.history_id = client.current_history_id()
    except GmailAuthError:
        connection_service.mark_reauth_required(connection)
        report = SyncReport(reauth_required=True)
    connection.last_sync_at = timezone.now()
    connection.save(update_fields=["last_sync_at", "history_id", "updated_at"])
    return report


def sync_from_history(connection: GmailConnection) -> SyncReport:
    """Process what arrived since the stored checkpoint (push notifications use this).

    The first run only records the starting point: mail from before the connection is
    never imported."""
    client = clients.get_gmail_client(connection)
    report = SyncReport()
    try:
        if not connection.history_id:
            connection.history_id = client.current_history_id()
        else:
            try:
                result = client.list_history(connection.history_id)
            except GmailRejectedError:  # checkpoint too old: restart from now
                logger.warning("Gmail history checkpoint expired; resetting")
                connection.history_id = client.current_history_id()
            else:
                report = _process_ids(connection, client, result.message_ids)
                connection.history_id = result.history_id or connection.history_id
    except GmailAuthError:
        connection_service.mark_reauth_required(connection)
        report.reauth_required = True
    connection.last_sync_at = timezone.now()
    connection.save(update_fields=["last_sync_at", "history_id", "updated_at"])
    return report
