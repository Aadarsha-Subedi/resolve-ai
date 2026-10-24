from django.db import models


class ConnectionStatus(models.TextChoices):
    CONNECTED = "connected", "Connected"
    # Signed in without a usable Gmail grant (declined, or Google sent no refresh token).
    NOT_CONNECTED = "not_connected", "Not connected"
    # The stored token stopped working (revoked, expired in Testing mode).
    REAUTH_REQUIRED = "reauth_required", "Sign in again"
    DISCONNECTED = "disconnected", "Disconnected"


class SyncOutcome(models.TextChoices):
    MATCHED = "matched", "Matched"
    REVIEW = "review", "Needs review"
    DUPLICATE = "duplicate", "Duplicate"
    IGNORED = "ignored", "Ignored"
