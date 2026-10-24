from datetime import timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from accounts.constants import errors, messages
from accounts.models import User
from accounts.services import hooks, session_service
from common.exception.domain import ConflictException


def ownership_blockers(user: User) -> list[str]:
    return [reason for check in hooks.ownership_checks if (reason := check(user))]


def request_deletion(request: HttpRequest, user: User) -> None:
    """Start the grace period, end every session. Blocked while the user owns something."""
    blockers = ownership_blockers(user)
    if blockers:
        raise ConflictException(
            messages.MESSAGE_OWNERSHIP_BLOCKED,
            errors=[{"field": "account", "message": reason} for reason in blockers],
            error_code=errors.ERROR_OWNERSHIP_BLOCKED,
        )
    user.deletion_requested_at = timezone.now()
    user.save(update_fields=["deletion_requested_at", "updated_at"])
    session_service.end_all_sessions(user)
    logout(request)
    hooks.emit(user, hooks.ACTION_DELETION_REQUESTED)


def cancel_deletion(user: User) -> bool:
    """Signing in during the grace period cancels the deletion."""
    if user.deletion_requested_at is None:
        return False
    user.deletion_requested_at = None
    user.save(update_fields=["deletion_requested_at", "updated_at"])
    hooks.emit(user, hooks.ACTION_DELETION_CANCELLED)
    return True


def purge_due_accounts() -> int:
    """Hard-delete accounts whose grace period is over. Returns how many were deleted."""
    cutoff = timezone.now() - timedelta(days=settings.ACCOUNT_DELETION_GRACE_DAYS)
    count = 0
    for user in User.objects.filter(deletion_requested_at__lte=cutoff).iterator():
        with transaction.atomic():
            hooks.emit(user, hooks.ACTION_DELETED)
            user.delete()
        count += 1
    return count
