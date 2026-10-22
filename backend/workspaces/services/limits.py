"""How many workspaces one user may own (USER_MAX_OWNED_WORKSPACES)."""

from django.conf import settings

from accounts.models import User
from common.exception.domain import ConflictException
from workspaces.constants.roles import MembershipStatus, Role
from workspaces.models import WorkspaceMembership


def owned_count(user_id) -> int:
    return WorkspaceMembership.objects.filter(
        user_id=user_id,
        role=Role.OWNER,
        status=MembershipStatus.ACTIVE,
        workspace__is_deleted=False,
    ).count()


def ensure_can_own_another(user_id, message: str, error_code: str) -> None:
    """Raise 409 when the user already owns the maximum. Call inside a transaction:
    the user row is locked so two simultaneous requests cannot both pass the check."""
    User.objects.select_for_update().filter(pk=user_id).first()
    limit = settings.USER_MAX_OWNED_WORKSPACES
    if owned_count(user_id) >= limit:
        raise ConflictException(message.format(limit=limit), error_code=error_code)
