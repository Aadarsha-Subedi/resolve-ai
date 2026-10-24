import hashlib
import random

from django.core.cache import cache

from common.email.utils import normalize_email
from common.exception.domain import NotFoundException, ThrottledException
from common.storage import get_storage
from tickets.constants import errors, messages
from tickets.constants.enums import TicketSource
from tickets.constants.settings import (
    DEFAULT_CATEGORY,
    DEFAULT_PRIORITY,
    PORTAL_EMAIL_CACHE_KEY,
    PORTAL_EMAIL_LIMIT,
    PORTAL_EMAIL_WINDOW_SECONDS,
    PORTAL_FAKE_NUMBER_RANGE,
)
from tickets.models import Ticket
from tickets.services import ticket_service
from workspaces.models import Workspace


def get_portal_workspace(slug: str) -> Workspace:
    """Unknown slug, deleted workspace and disabled portal all look the same: 404."""
    workspace = Workspace.objects.filter(slug=slug.lower(), portal_enabled=True).first()
    if workspace is None:
        raise NotFoundException(messages.MESSAGE_PORTAL_NOT_FOUND)
    return workspace


def portal_info(workspace: Workspace) -> dict:
    """Public data only: name, address, logo. Nothing about members or tickets."""
    return {
        "name": workspace.name,
        "slug": workspace.slug,
        "logo_url": get_storage().url(workspace.logo_key)
        if workspace.logo_key
        else None,
    }


def _email_limited(workspace_id, email: str) -> bool:
    key = PORTAL_EMAIL_CACHE_KEY.format(
        workspace_id=workspace_id, email_hash=hashlib.sha256(email.encode()).hexdigest()
    )
    cache.add(key, 0, timeout=PORTAL_EMAIL_WINDOW_SECONDS)
    try:
        return cache.incr(key) > PORTAL_EMAIL_LIMIT
    except ValueError:  # key expired between add and incr
        cache.set(key, 1, timeout=PORTAL_EMAIL_WINDOW_SECONDS)
        return False


def submit(slug: str, data: dict, honeypot_filled: bool) -> int:
    """Create a ticket from the public form and return its number.

    A filled honeypot gets a normal-looking answer and creates nothing."""
    workspace = get_portal_workspace(slug)
    if honeypot_filled:
        return random.randint(*PORTAL_FAKE_NUMBER_RANGE)
    email = normalize_email(data["customer_email"])
    if _email_limited(workspace.id, email):
        raise ThrottledException(
            messages.MESSAGE_PORTAL_RATE_LIMITED,
            error_code=errors.ERROR_PORTAL_RATE_LIMITED,
        )
    ticket: Ticket = ticket_service.create_ticket(
        workspace.id,
        subject=data["subject"],
        description=data["description"],
        customer_email=email,
        customer_name=data.get("customer_name", ""),
        category=data.get("category", DEFAULT_CATEGORY),
        priority=DEFAULT_PRIORITY,  # customers cannot set it
        source=TicketSource.PORTAL,
        confirmation_pending=True,
    )
    return ticket.number
