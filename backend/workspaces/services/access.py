"""Workspace isolation and RBAC. Non-members get 404, members without the permission 403."""

from uuid import UUID

from accounts.models import User
from common.exception.domain import NotFoundException, PermissionDeniedException
from workspaces.constants import messages
from workspaces.constants.permissions import ROLE_PERMISSIONS
from workspaces.constants.roles import MembershipStatus
from workspaces.models import WorkspaceMembership


def get_membership(user: User, workspace_id: UUID) -> WorkspaceMembership:
    """The user's ACTIVE membership in a live workspace, else 404 (never 403)."""
    membership = (
        WorkspaceMembership.objects.select_related("workspace")
        .filter(
            user=user,
            workspace_id=workspace_id,
            status=MembershipStatus.ACTIVE,
            workspace__is_deleted=False,
        )
        .first()
    )
    if membership is None:
        raise NotFoundException(messages.MESSAGE_WORKSPACE_NOT_FOUND)
    return membership


def has_permission(membership: WorkspaceMembership, code: str) -> bool:
    return membership.is_active and code in ROLE_PERMISSIONS.get(
        membership.role, frozenset()
    )


def require_permission(
    user: User, workspace_id: UUID, code: str
) -> WorkspaceMembership:
    membership = get_membership(user, workspace_id)
    if not has_permission(membership, code):
        raise PermissionDeniedException()
    return membership
