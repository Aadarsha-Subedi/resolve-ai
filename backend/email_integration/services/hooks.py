"""Audit extension point for Gmail connection changes (account-level: no workspace).
Never carries tokens or mail content."""

from django.dispatch import Signal

SENDER = "email_integration"
email_event = Signal()  # kwargs: user, action, metadata

ACTION_GMAIL_CONNECTED = "gmail.connected"
ACTION_GMAIL_REAUTH_REQUIRED = "gmail.reauth_required"
ACTION_GMAIL_DISCONNECTED = "gmail.disconnected"


def emit(user, action: str, **metadata) -> None:
    email_event.send(sender=SENDER, user=user, action=action, metadata=metadata)
