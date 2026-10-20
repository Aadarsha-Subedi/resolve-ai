import logging

import requests
from django.conf import settings
from django.utils import timezone

from accounts.models import User
from accounts.services.identity import get_google_subject
from email_integration import clients
from email_integration.clients.base import GmailError
from email_integration.constants import settings as cfg
from email_integration.constants.enums import ConnectionStatus
from email_integration.models import GmailConnection
from email_integration.services import token_service

logger = logging.getLogger(__name__)


def fetch_granted_scopes(access_token: str) -> set[str]:
    """Ask Google which scopes this token really carries (the user may have unticked some)."""
    try:
        response = requests.get(
            cfg.TOKENINFO_URL,
            params={"access_token": access_token},
            timeout=cfg.HTTP_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            return set(response.json().get("scope", "").split())
    except requests.RequestException:
        logger.warning("Could not read granted scopes from Google")
    return set()


def record_login_grant(user: User, sociallogin) -> GmailConnection | None:
    """Called after a Google sign-in: store the Gmail grant (encrypted) or mark it missing.

    Never raises: a Gmail problem must not stop someone from signing in."""
    token = getattr(sociallogin, "token", None)
    if token is None or not token.token:
        return None
    try:
        scopes = fetch_granted_scopes(token.token)
        refresh = token.token_secret or ""
        connection = GmailConnection.objects.filter(user=user).first()
        has_scopes = cfg.REQUIRED_SCOPES <= scopes
        if connection is None:
            connection = GmailConnection(
                user=user,
                google_subject=get_google_subject(user) or sociallogin.account.uid,
                mailbox_email=user.email,
            )
        connection.granted_scopes = sorted(scopes)
        if not has_scopes:
            # Declined or removed: keep nothing that could be used for Gmail.
            connection.encrypted_refresh_token = ""
            connection.status = ConnectionStatus.NOT_CONNECTED
        elif refresh:
            connection.encrypted_refresh_token = token_service.encrypt_refresh_token(
                refresh
            )
            connection.status = ConnectionStatus.CONNECTED
            connection.connected_at = timezone.now()
        elif connection.encrypted_refresh_token:
            # Google sends the refresh token only on the first consent: keep the stored one.
            connection.status = ConnectionStatus.CONNECTED
        else:
            connection.status = ConnectionStatus.NOT_CONNECTED
        connection.mailbox_email = user.email
        connection.save()
    except Exception:
        logger.exception("Could not record the Gmail grant")
        return None
    return connection


def get_connection(user: User) -> GmailConnection | None:
    return GmailConnection.objects.filter(user=user).first()


def mark_reauth_required(connection: GmailConnection) -> None:
    connection.status = ConnectionStatus.REAUTH_REQUIRED
    connection.save(update_fields=["status", "updated_at"])


def disconnect(user: User) -> GmailConnection | None:
    """Stop using Gmail: stop the watch, revoke the grant at Google, delete our copy."""
    connection = get_connection(user)
    if connection is None:
        return None
    if connection.is_connected:
        try:
            client = clients.get_gmail_client(connection)
            if connection.watch_expires_at:
                client.stop_watch()
            client.revoke()
        except Exception:  # noqa: BLE001  best effort: our copy is deleted either way
            logger.warning("Gmail revoke failed during disconnect")
    connection.encrypted_refresh_token = ""
    connection.status = ConnectionStatus.DISCONNECTED
    connection.history_id = ""
    connection.watch_expires_at = None
    connection.save()
    return connection


def watch_enabled() -> bool:
    return bool(settings.GMAIL_PUBSUB_TOPIC)


def ensure_watch(connection: GmailConnection) -> None:
    """Register for push notifications and remember the starting history position."""
    if not (watch_enabled() and connection.is_connected):
        return
    try:
        client = clients.get_gmail_client(connection)
        result = client.watch(settings.GMAIL_PUBSUB_TOPIC)
    except GmailError:
        logger.warning("Could not set up the Gmail watch")
        return
    connection.watch_expires_at = result.expires_at
    if not connection.history_id:
        connection.history_id = result.history_id
    connection.save(update_fields=["watch_expires_at", "history_id", "updated_at"])
