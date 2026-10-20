"""WorkspaceAccessPolicy: boolean questions for views/services that cannot raise."""

from workspaces.constants import permissions
from workspaces.models import WorkspaceMembership
from workspaces.services.access import has_permission


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
