from django.db import transaction
from django.db.models import QuerySet

from accounts.models import User
from common.exception.domain import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from workspaces.constants import errors, messages, permissions
from workspaces.constants.roles import MembershipStatus, Role
from workspaces.models import WorkspaceMembership
from workspaces.services import access, hooks, limits


def list_members(user: User, workspace_id) -> QuerySet[WorkspaceMembership]:
    access.require_permission(user, workspace_id, permissions.MEMBERS_VIEW)
    return (
        WorkspaceMembership.objects.select_related("user")
        .filter(workspace_id=workspace_id, status=MembershipStatus.ACTIVE)
        .order_by("joined_at", "id")
    )


def remove_member(actor: User, workspace_id, member_user_id) -> None:
    owner_membership = access.require_permission(
        actor, workspace_id, permissions.MEMBERS_REMOVE
    )
    target = WorkspaceMembership.objects.filter(
        workspace_id=workspace_id,
        user_id=member_user_id,
        status=MembershipStatus.ACTIVE,
    ).first()
    if target is None:
        raise NotFoundException(messages.MESSAGE_MEMBER_NOT_FOUND)
    if target.role == Role.OWNER:
        raise ConflictException(
            messages.MESSAGE_CANNOT_REMOVE_OWNER,
            error_code=errors.ERROR_CANNOT_REMOVE_OWNER,
        )
    target.status = MembershipStatus.REMOVED
    target.save(update_fields=["status", "updated_at"])
    hooks.emit(
        owner_membership.workspace,
        actor,
        hooks.ACTION_MEMBER_REMOVED,
        user_id=str(member_user_id),
    )


def leave_workspace(user: User, workspace_id) -> None:
    membership = access.get_membership(user, workspace_id)
    if membership.role == Role.OWNER:
        raise ConflictException(
            messages.MESSAGE_OWNER_CANNOT_LEAVE,
            error_code=errors.ERROR_OWNER_CANNOT_LEAVE,
        )
    membership.status = MembershipStatus.REMOVED
    membership.save(update_fields=["status", "updated_at"])
    hooks.emit(membership.workspace, user, hooks.ACTION_MEMBER_LEFT)


def transfer_ownership(actor: User, workspace_id, new_owner_id) -> None:
    """Promote the target and demote the actor in one transaction."""
    access.require_permission(actor, workspace_id, permissions.OWNERSHIP_TRANSFER)
    if new_owner_id == actor.id:
        raise BadRequestException(
            messages.MESSAGE_TRANSFER_TO_SELF, error_code=errors.ERROR_TRANSFER_TO_SELF
        )
    with transaction.atomic():
        rows = {
            m.user_id: m
            for m in WorkspaceMembership.objects.select_for_update()
            .select_related("workspace")
            .filter(
                workspace_id=workspace_id,
                user_id__in=[actor.id, new_owner_id],
                status=MembershipStatus.ACTIVE,
            )
        }
        current, target = rows.get(actor.id), rows.get(new_owner_id)
        if current is None or current.role != Role.OWNER:
            # Lost the race with another transfer: behave like a non-owner.
            raise ConflictException(messages.MESSAGE_WORKSPACE_NOT_FOUND)
        if target is None:
            raise BadRequestException(
                messages.MESSAGE_TRANSFER_TARGET_INVALID,
                error_code=errors.ERROR_TRANSFER_TARGET_INVALID,
            )
        limits.ensure_can_own_another(
            new_owner_id,
            messages.MESSAGE_TRANSFER_TARGET_AT_LIMIT,
            errors.ERROR_TRANSFER_TARGET_AT_LIMIT,
        )
        # Demote first: only one ACTIVE owner may exist at any moment.
        current.role = Role.MEMBER
        current.save(update_fields=["role", "updated_at"])
        target.role = Role.OWNER
        target.save(update_fields=["role", "updated_at"])
    hooks.emit(
        current.workspace,
        actor,
        hooks.ACTION_OWNERSHIP_TRANSFERRED,
        new_owner_id=str(new_owner_id),
    )


def add_member(workspace, user: User) -> tuple[WorkspaceMembership, bool]:
    """Make `user` an active MEMBER (re-activating a removed one). Returns (membership, created)."""
    membership, created = WorkspaceMembership.objects.get_or_create(
        workspace=workspace, user=user, defaults={"role": Role.MEMBER}
    )
    if not created and membership.status != MembershipStatus.ACTIVE:
        membership.status = MembershipStatus.ACTIVE
        membership.role = Role.MEMBER
        membership.save(update_fields=["status", "role", "updated_at"])
        created = True
    if created:
        hooks.emit(workspace, user, hooks.ACTION_MEMBER_JOINED)
    return membership, created
