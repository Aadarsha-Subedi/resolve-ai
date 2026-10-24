"""Authenticating and decoding Gmail push notifications from Google Pub/Sub.

The push subscription must use authentication: Pub/Sub then sends a Google-signed JWT whose
audience is our endpoint URL and whose `email` is the subscription's service account."""

import base64
import json
import logging

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from common.exception.domain import AuthenticationDeniedException, NotFoundException
from email_integration.constants import errors, messages
from email_integration.constants import settings as cfg

logger = logging.getLogger(__name__)


def push_enabled() -> bool:
    return bool(settings.PUBSUB_PUSH_AUDIENCE and settings.PUBSUB_PUSH_SERVICE_ACCOUNT)


def verify_request(authorization_header: str) -> None:
    if not push_enabled():
        raise NotFoundException(
            messages.MESSAGE_PUSH_DISABLED, error_code=errors.ERROR_PUSH_DISABLED
        )
    scheme, _, token = (authorization_header or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized()
    try:
        claims = id_token.verify_oauth2_token(
            token, google_requests.Request(), audience=settings.PUBSUB_PUSH_AUDIENCE
        )
    except ValueError:
        raise _unauthorized() from None
    if (
        claims.get("iss") not in cfg.PUBSUB_ISSUERS
        or claims.get("email") != settings.PUBSUB_PUSH_SERVICE_ACCOUNT
        or not claims.get("email_verified")
    ):
        raise _unauthorized()


def decode_notification(body: dict) -> tuple[str, str] | None:
    """(mailbox email, history id) from a Pub/Sub push body, or None if malformed."""
    try:
        data = json.loads(base64.b64decode(body["message"]["data"]))
        return str(data["emailAddress"]).lower(), str(data["historyId"])
    except KeyError, TypeError, ValueError:
        return None


def _unauthorized() -> AuthenticationDeniedException:
    return AuthenticationDeniedException(
        messages.MESSAGE_PUSH_UNAUTHORIZED, error_code=errors.ERROR_PUSH_UNAUTHORIZED
    )
