"""RBAC permission codes and the fixed role presets (not editable per member).

Later features add their codes here and to ROLE_PERMISSIONS. State-based (ABAC)
rules live in each feature's policies module and only ever narrow these grants.
"""

from workspaces.constants.roles import Role

WORKSPACE_VIEW = "workspace.view"
WORKSPACE_UPDATE = "workspace.update"
WORKSPACE_DELETE = "workspace.delete"
MEMBERS_VIEW = "members.view"
MEMBERS_REMOVE = "members.remove"
OWNERSHIP_TRANSFER = "ownership.transfer"
JOIN_LINK_MANAGE = "join_link.manage"
INVITATIONS_MANAGE = "invitations.manage"

_MEMBER_PERMISSIONS = frozenset({WORKSPACE_VIEW, MEMBERS_VIEW})

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    Role.MEMBER: _MEMBER_PERMISSIONS,
    Role.OWNER: _MEMBER_PERMISSIONS
    | {
        WORKSPACE_UPDATE,
        WORKSPACE_DELETE,
        MEMBERS_REMOVE,
        OWNERSHIP_TRANSFER,
        JOIN_LINK_MANAGE,
        INVITATIONS_MANAGE,
    },
}
