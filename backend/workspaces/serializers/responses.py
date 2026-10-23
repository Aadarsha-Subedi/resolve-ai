from dataclasses import dataclass

from common.response.domain import BaseResponseData
from workspaces.models import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceJoinLink,
    WorkspaceMembership,
)
from workspaces.services.join_link_service import IssuedLink
from workspaces.services.logo_service import logo_url


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def workspace_dict(workspace: Workspace) -> dict:
    return {
        "id": str(workspace.id),
        "name": workspace.name,
        "slug": workspace.slug,
        "logo_url": logo_url(workspace),
        "portal_enabled": workspace.portal_enabled,
        "is_demo": workspace.is_demo,
        "search_language": workspace.search_language,
        "created_at": workspace.created_at.isoformat(),
    }


@dataclass(frozen=True)
class WorkspaceData(BaseResponseData):
    membership: WorkspaceMembership

    def to_dict(self) -> dict:
        return {
            **workspace_dict(self.membership.workspace),
            "role": self.membership.role,
        }


@dataclass(frozen=True)
class MemberData(BaseResponseData):
    membership: WorkspaceMembership

    def to_dict(self) -> dict:
        m = self.membership
        return {
            "user_id": str(m.user_id),
            "email": m.user.email,
            "display_name": m.user.display_name,
            "avatar_url": m.user.avatar_url,
            "role": m.role,
            "joined_at": m.joined_at.isoformat(),
        }


@dataclass(frozen=True)
class JoinLinkData(BaseResponseData):
    link: WorkspaceJoinLink | None

    def to_dict(self) -> dict:
        link = self.link
        if link is None:
            return {"active": False}
        return {
            "active": True,
            "created_at": link.created_at.isoformat(),
            "expires_at": link.expires_at.isoformat(),
        }


@dataclass(frozen=True)
class IssuedJoinLinkData(BaseResponseData):
    issued: IssuedLink

    def to_dict(self) -> dict:
        return {
            "active": True,
            "token": self.issued.raw_token,
            "url": self.issued.url,
            "created_at": self.issued.link.created_at.isoformat(),
            "expires_at": self.issued.link.expires_at.isoformat(),
        }


@dataclass(frozen=True)
class InvitationData(BaseResponseData):
    invitation: WorkspaceInvitation
    outcome: str | None = None

    def to_dict(self) -> dict:
        i = self.invitation
        data = {
            "id": str(i.id),
            "email": i.email,
            "created_at": i.created_at.isoformat(),
            "expires_at": i.expires_at.isoformat(),
        }
        return {**data, "outcome": self.outcome} if self.outcome else data


@dataclass(frozen=True)
class MyInvitationData(BaseResponseData):
    invitation: WorkspaceInvitation

    def to_dict(self) -> dict:
        i = self.invitation
        return {
            "id": str(i.id),
            "workspace": {
                "id": str(i.workspace_id),
                "name": i.workspace.name,
                "slug": i.workspace.slug,
            },
            "expires_at": _iso(i.expires_at),
        }


@dataclass(frozen=True)
class InvitationOutcomeData(BaseResponseData):
    email: str
    outcome: str
    invitation: WorkspaceInvitation | None

    def to_dict(self) -> dict:
        return {
            "email": self.email,
            "outcome": self.outcome,
            "invitation": (
                InvitationData(self.invitation).to_dict() if self.invitation else None
            ),
        }


@dataclass(frozen=True)
class DictData(BaseResponseData):
    """Small ad-hoc payloads (upload URL, message-only results)."""

    payload: dict

    def to_dict(self) -> dict:
        return self.payload
