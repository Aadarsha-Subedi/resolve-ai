"""Extension points other features plug into.

- `ownership_checks`: workspaces (feature 3) registers a check that returns a reason
  string while the user still owns something, or None when deletion is fine.
- `account_event`: audit (feature 2) connects to this signal. No one listens yet.
"""

from collections.abc import Callable

from django.dispatch import Signal

from accounts.models import User

OwnershipCheck = Callable[[User], str | None]

ownership_checks: list[OwnershipCheck] = []

# Sent with `user`, `action` (an ACTION_* value) and `metadata` (a dict without secrets).
account_event = Signal()

ACTION_LOGIN = "login"
ACTION_LOGOUT = "logout"
ACTION_LOGOUT_ALL = "logout_all"
ACTION_SESSION_REVOKED = "session_revoked"
ACTION_PROFILE_UPDATED = "profile_updated"
ACTION_DELETION_REQUESTED = "deletion_requested"
ACTION_DELETION_CANCELLED = "deletion_cancelled"
ACTION_DELETED = "deleted"


def register_ownership_check(check: OwnershipCheck) -> None:
    if check not in ownership_checks:
        ownership_checks.append(check)


def emit(user: User, action: str, **metadata) -> None:
    account_event.send(sender=User, user=user, action=action, metadata=metadata)
