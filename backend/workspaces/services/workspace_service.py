import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.template.defaultfilters import slugify
from django.utils import timezone

from accounts.models import User
from common.exception.domain import ConflictException, ValidationException
from workspaces.constants import errors, messages, permissions
from workspaces.constants.roles import MembershipStatus, Role
from workspaces.constants.settings import (
    RESERVED_SLUGS,
    SLUG_MAX_ATTEMPTS,
    SLUG_MAX_LENGTH,
    SLUG_SUFFIX_BYTES,
)
from workspaces.models import Workspace, WorkspaceMembership
from workspaces.services import access, hooks, limits


def _derive_slug(name: str) -> str:
    base = slugify(name)[: SLUG_MAX_LENGTH - 5].strip("-") or "workspace"
    base = re.sub(r"-{2,}", "-", base)
    return f"{base}-{secrets.token_hex(SLUG_SUFFIX_BYTES)}"


def create_workspace(user: User, name: str, slug: str | None) -> Workspace:
    """Create a workspace and make the creator its owner."""
    if slug is not None and slug in RESERVED_SLUGS:
        raise ValidationException(
            messages.MESSAGE_SLUG_RESERVED, error_code=errors.ERROR_SLUG_RESERVED
        )
    attempts = 1 if slug else SLUG_MAX_ATTEMPTS
    for _ in range(attempts):
        candidate = slug or _derive_slug(name)
        try:
            with transaction.atomic():
                limits.ensure_can_own_another(
                    user.id,
                    messages.MESSAGE_WORKSPACE_LIMIT_REACHED,
                    errors.ERROR_WORKSPACE_LIMIT_REACHED,
                )
                workspace = Workspace.objects.create(
                    name=name, slug=candidate, created_by=user
                )
                WorkspaceMembership.objects.create(
                    workspace=workspace, user=user, role=Role.OWNER
                )
        except IntegrityError:
            continue
        hooks.emit(workspace, user, hooks.ACTION_CREATED)
        return workspace
    raise ConflictException(
        messages.MESSAGE_SLUG_TAKEN, error_code=errors.ERROR_SLUG_TAKEN
    )


def list_workspaces(user: User) -> QuerySet[WorkspaceMembership]:
    """The user's active memberships (with workspace), newest first."""
    return (
        WorkspaceMembership.objects.select_related("workspace")
        .filter(
            user=user,
            status=MembershipStatus.ACTIVE,
            workspace__is_deleted=False,
        )
        .order_by("-joined_at", "id")
    )


def update_workspace(
    user: User,
    workspace_id,
    name: str | None,
    portal_enabled: bool | None,
    search_language: str | None = None,
) -> WorkspaceMembership:
    membership = access.require_permission(
        user, workspace_id, permissions.WORKSPACE_UPDATE
    )
    workspace = membership.workspace
    changed = []
    if name is not None and name != workspace.name:
        workspace.name = name
        changed.append("name")
    if portal_enabled is not None and portal_enabled != workspace.portal_enabled:
        workspace.portal_enabled = portal_enabled
        changed.append("portal_enabled")
    if search_language is not None and search_language != workspace.search_language:
        workspace.search_language = search_language
        changed.append("search_language")
    if changed:
        workspace.save(update_fields=[*changed, "updated_at"])
        hooks.emit(workspace, user, hooks.ACTION_UPDATED, fields=changed)
    return membership


def delete_workspace(user: User, workspace_id) -> None:
    """Soft-delete now; `purge_due_workspaces` removes it after the grace period."""
    membership = access.require_permission(
        user, workspace_id, permissions.WORKSPACE_DELETE
    )
    workspace = membership.workspace
    workspace.delete()
    hooks.emit(workspace, user, hooks.ACTION_DELETED)


def purge_due_workspaces() -> int:
    """Hard-delete workspaces whose grace period is over. Returns how many were removed."""
    cutoff = timezone.now() - timedelta(days=settings.WORKSPACE_DELETION_GRACE_DAYS)
    due = Workspace.all_objects.filter(is_deleted=True, deleted_at__lte=cutoff)
    count = 0
    for workspace in due.iterator():
        with transaction.atomic():
            hooks.emit(workspace, None, hooks.ACTION_PURGED)
            if workspace.logo_key:
                _delete_logo(workspace.logo_key)
            Workspace.all_objects.filter(pk=workspace.pk).delete()
        count += 1
    return count


def _delete_logo(key: str) -> None:
    from common.storage import get_storage

    get_storage().delete(key)
