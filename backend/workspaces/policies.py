"""WorkspaceAccessPolicy: boolean questions for views/services that cannot raise.

`ensure_not_demo` is a fixed ABAC rule: a demo workspace is private to its one owner, so
it never gets a portal, invitations, join links, new members or a new owner.
"""

from common.exception.domain import ConflictException
from workspaces.constants import errors, messages, permissions
from workspaces.models import Workspace, WorkspaceMembership
from workspaces.services.access import has_permission


def ensure_not_demo(workspace: Workspace) -> None:
    if workspace.is_demo:
        raise ConflictException(
            messages.MESSAGE_DEMO_PRIVATE, error_code=errors.ERROR_DEMO_WORKSPACE
        )


class WorkspaceAccessPolicy:
    @staticmethod
    def can_access_workspace(membership: WorkspaceMembership | None) -> bool:
        return membership is not None and has_permission(
            membership, permissions.WORKSPACE_VIEW
        )

    @staticmethod
    def can_manage_members(membership: WorkspaceMembership) -> bool:
        return has_permission(membership, permissions.MEMBERS_REMOVE)

    @staticmethod
    def can_rotate_join_link(membership: WorkspaceMembership) -> bool:
        return has_permission(membership, permissions.JOIN_LINK_MANAGE)

    @staticmethod
    def can_transfer_ownership(membership: WorkspaceMembership) -> bool:
        return has_permission(membership, permissions.OWNERSHIP_TRANSFER)

    @staticmethod
    def can_delete_workspace(membership: WorkspaceMembership) -> bool:
        return has_permission(membership, permissions.WORKSPACE_DELETE)
