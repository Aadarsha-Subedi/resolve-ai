from accounts.models import User
from workspaces.constants.roles import MembershipStatus, Role
from workspaces.models import WorkspaceMembership


def account_ownership_blocker(user: User) -> str | None:
    """Registered with accounts: a user who still owns a workspace cannot delete their account."""
    names = list(
        WorkspaceMembership.objects.filter(
            user=user,
            role=Role.OWNER,
            status=MembershipStatus.ACTIVE,
            workspace__is_deleted=False,
        ).values_list("workspace__name", flat=True)[:3]
    )
    if not names:
        return None
    return f"You own the workspace {', '.join(names)}. Transfer ownership or delete it first."
