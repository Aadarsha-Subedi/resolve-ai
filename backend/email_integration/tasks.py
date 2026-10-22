import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from email_integration.constants import settings as cfg
from email_integration.constants.enums import ConnectionStatus
from email_integration.models import GmailConnection
from email_integration.services import (
    connection_service,
    inbound_service,
    review_service,
    send_service,
)

logger = logging.getLogger(__name__)


@shared_task(
    name=cfg.TASK_SEND_MESSAGE,
    bind=True,
    autoretry_for=(send_service.RetryableSendError,),
    max_retries=cfg.SEND_MAX_RETRIES,
    retry_backoff=cfg.SEND_RETRY_BACKOFF_SECONDS,
    retry_jitter=True,
)
def send_ticket_message(self, message_id: str) -> None:
    send_service.send_ticket_message(
        message_id, final_attempt=self.request.retries >= cfg.SEND_MAX_RETRIES
    )


@shared_task(name=cfg.TASK_SEND_CONFIRMATION)
def send_portal_confirmation(ticket_id: str) -> None:
    send_service.send_portal_confirmation(ticket_id)


@shared_task(name=cfg.TASK_SEND_INVITATION)
def send_invitation_email(invitation_id: str) -> None:
    send_service.send_invitation_email(invitation_id)


@shared_task(name=cfg.TASK_SYNC_MAILBOX)
def sync_mailbox(connection_id: str) -> None:
    connection = GmailConnection.objects.filter(pk=connection_id).first()
    if connection is not None and connection.is_connected:
        inbound_service.sync_from_history(connection)


@shared_task(name=cfg.TASK_ENSURE_WATCH)
def ensure_gmail_watch(connection_id: str) -> None:
    connection = GmailConnection.objects.filter(pk=connection_id).first()
    if connection is not None:
        connection_service.ensure_watch(connection)


@shared_task(name=cfg.TASK_RENEW_WATCHES)
def renew_gmail_watches() -> int:
    """Gmail watches expire after about 7 days: renew the ones ending soon."""
    soon = timezone.now() + timedelta(days=cfg.WATCH_RENEW_BEFORE_DAYS)
    renewed = 0
    due = GmailConnection.objects.filter(status=ConnectionStatus.CONNECTED).filter(
        watch_expires_at__isnull=False, watch_expires_at__lte=soon
    )
    for connection in due:
        connection_service.ensure_watch(connection)
        renewed += 1
    return renewed


@shared_task(name=cfg.TASK_PURGE_REVIEW)
def purge_old_review_items() -> int:
    return review_service.purge_old_items()
