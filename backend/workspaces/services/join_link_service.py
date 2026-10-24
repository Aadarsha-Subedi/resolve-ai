import hashlib
import hmac
import secrets
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from common.exception.domain import NotFoundException
from workspaces.constants import errors, messages, permissions
from workspaces.constants.settings import (
    JOIN_LINK_DEFAULT_EXPIRY,
    JOIN_LINK_EXPIRY_CHOICES,
    JOIN_LINK_TOKEN_BYTES,
    JOIN_LINK_URL_PATH,
)
from workspaces.models import WorkspaceJoinLink, WorkspaceMembership
from workspaces.policies import ensure_not_demo
from workspaces.services import access, hooks, member_service


@dataclass(frozen=True)
class IssuedLink:
    link: WorkspaceJoinLink
    raw_token: str  # shown to the owner once, never stored

    @property
    def url(self) -> str:
        return settings.FRONTEND_URL.rstrip("/") + JOIN_LINK_URL_PATH.format(
            token=self.raw_token
        )


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def current_link(user: User, workspace_id) -> WorkspaceJoinLink | None:
    """Metadata of the live link (no token: it cannot be recovered)."""
    access.require_permission(user, workspace_id, permissions.JOIN_LINK_MANAGE)
    link = WorkspaceJoinLink.objects.filter(
        workspace_id=workspace_id, revoked_at__isnull=True
    ).first()
    return link if link and link.is_usable() else None


def rotate_link(
    user: User, workspace_id, expires_in: str = JOIN_LINK_DEFAULT_EXPIRY
) -> IssuedLink:
    """Revoke the live link (if any) and issue a new one."""
    membership = access.require_permission(
        user, workspace_id, permissions.JOIN_LINK_MANAGE
    )
    ensure_not_demo(membership.workspace)
    raw = secrets.token_urlsafe(JOIN_LINK_TOKEN_BYTES)
    now = timezone.now()
    with transaction.atomic():
        WorkspaceJoinLink.objects.filter(
            workspace_id=workspace_id, revoked_at__isnull=True
        ).update(revoked_at=now)
        link = WorkspaceJoinLink.objects.create(
            workspace_id=workspace_id,
            token_hash=hash_token(raw),
            created_by=user,
            expires_at=now + JOIN_LINK_EXPIRY_CHOICES[expires_in],
        )
    hooks.emit(
        membership.workspace,
        user,
        hooks.ACTION_JOIN_LINK_CREATED,
        expires_in=expires_in,
    )
    return IssuedLink(link=link, raw_token=raw)


def revoke_link(user: User, workspace_id) -> None:
    membership = access.require_permission(
        user, workspace_id, permissions.JOIN_LINK_MANAGE
    )
    revoked = WorkspaceJoinLink.objects.filter(
        workspace_id=workspace_id, revoked_at__isnull=True
    ).update(revoked_at=timezone.now())
    if revoked:
        hooks.emit(membership.workspace, user, hooks.ACTION_JOIN_LINK_REVOKED)


def redeem(user: User, raw_token: str) -> tuple[WorkspaceMembership, bool]:
    """Join the workspace behind a valid link. Returns (membership, newly_joined)."""
    link = (
        WorkspaceJoinLink.objects.select_related("workspace")
        .filter(token_hash=hash_token(raw_token))
        .first()
    )
    # Constant-time comparison is unnecessary for a hashed lookup, but keep the
    # failure indistinguishable: unknown, expired, revoked and deleted all look alike.
    if (
        link is None
        or not hmac.compare_digest(link.token_hash, hash_token(raw_token))
        or not link.is_usable()
        or link.workspace.is_deleted
    ):
        raise NotFoundException(
            messages.MESSAGE_JOIN_LINK_INVALID,
            error_code=errors.ERROR_JOIN_LINK_INVALID,
        )
    return member_service.add_member(link.workspace, user)
