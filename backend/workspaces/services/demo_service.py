"""The per-user demo workspace: created on first sign-in (or from "Explore demo"),
private to its one owner, filled with sample content by the apps that own that content.

Feature apps register a `DemoContent` (seed + clear) at startup, the same way accounts'
ownership checks work, so this module never imports them.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import User
from common.exception.domain import ConflictException
from workspaces.constants import errors, messages, permissions
from workspaces.constants.roles import MembershipStatus, Role
from workspaces.constants.settings import DEMO_WORKSPACE_NAME, SLUG_MAX_ATTEMPTS
from workspaces.models import Workspace, WorkspaceMembership
from workspaces.services import access, hooks
from workspaces.services.workspace_service import derive_slug

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DemoContent:
    name: str
    seed: Callable[[Workspace, User], None]
    clear: Callable[[Workspace], None]


demo_contents: list[DemoContent] = []


def register_demo_content(content: DemoContent) -> None:
    if all(c.name != content.name for c in demo_contents):
        demo_contents.append(content)


def live_demo(user: User) -> WorkspaceMembership | None:
    return (
        WorkspaceMembership.objects.select_related("workspace")
        .filter(
            user=user,
            role=Role.OWNER,
            status=MembershipStatus.ACTIVE,
            workspace__is_demo=True,
            workspace__is_deleted=False,
        )
        .first()
    )


def _create(user: User) -> WorkspaceMembership:
    """Workspace, owner membership and sample content in one transaction. No member-limit
    check: the demo does not count toward it."""
    for _ in range(SLUG_MAX_ATTEMPTS):
        try:
            with transaction.atomic():
                workspace = Workspace.objects.create(
                    name=DEMO_WORKSPACE_NAME,
                    slug=derive_slug("demo"),
                    created_by=user,
                    is_demo=True,
                    portal_enabled=False,
                )
                membership = WorkspaceMembership.objects.create(
                    workspace=workspace, user=user, role=Role.OWNER
                )
                for content in demo_contents:
                    content.seed(workspace, user)
                if user.demo_provisioned_at is None:
                    user.demo_provisioned_at = timezone.now()
                    user.save(update_fields=["demo_provisioned_at", "updated_at"])
        except IntegrityError:
            continue  # slug collision: try another suffix
        hooks.emit(workspace, user, hooks.ACTION_CREATED, demo=True)
        return membership
    raise ConflictException(
        messages.MESSAGE_SLUG_TAKEN, error_code=errors.ERROR_SLUG_TAKEN
    )


def provision_on_sign_in(user: User) -> None:
    """Called after every Google sign-in. Creates the demo once per account; a failure is
    logged and retried on the next sign-in, never blocking the sign-in itself."""
    if user.demo_provisioned_at is not None:
        return
    try:
        _create(user)
    except Exception:
        logger.exception("Could not create the demo workspace")


def explore_demo(user: User) -> tuple[WorkspaceMembership, bool]:
    """The user's live demo, created if they have none. Returns (membership, created)."""
    existing = live_demo(user)
    if existing is not None:
        return existing, False
    return _create(user), True


def reset_demo(user: User, workspace_id) -> WorkspaceMembership:
    """Throw away everything the registered apps seeded (and anything added since) and seed
    it again. Only the owner, only on a demo workspace."""
    membership = access.require_permission(
        user, workspace_id, permissions.WORKSPACE_UPDATE
    )
    workspace = membership.workspace
    if not workspace.is_demo:
        raise ConflictException(
            messages.MESSAGE_NOT_DEMO_WORKSPACE,
            error_code=errors.ERROR_NOT_DEMO_WORKSPACE,
        )
    with transaction.atomic():
        for content in demo_contents:
            content.clear(workspace)
        for content in demo_contents:
            content.seed(workspace, user)
    hooks.emit(workspace, user, hooks.ACTION_DEMO_RESET)
    return access.get_membership(user, workspace_id)


def delete_demos_of(user: User) -> None:
    """Account purge: a demo has no one else to hand it to, so it goes with its owner.
    Soft delete, so `purge_due_workspaces` removes it (and its files) as usual."""
    ids = WorkspaceMembership.objects.filter(
        user=user, role=Role.OWNER, workspace__is_demo=True
    ).values_list("workspace_id", flat=True)
    Workspace.objects.filter(pk__in=list(ids)).delete()
