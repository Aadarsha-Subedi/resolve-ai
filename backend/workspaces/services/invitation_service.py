from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from accounts.models import User
from common.email.utils import canonical_email_key
from common.exception.domain import ConflictException, NotFoundException
from workspaces.constants import errors, messages, permissions
from workspaces.constants.roles import MembershipStatus
from workspaces.constants.settings import INVITATION_EXPIRY
from workspaces.models import WorkspaceInvitation, WorkspaceMembership
from workspaces.services import access, hooks, member_service

OUTCOME_CREATED = "created"
OUTCOME_ALREADY_INVITED = "already_invited"
OUTCOME_ALREADY_MEMBER = "already_member"


@dataclass(frozen=True)
class InvitationOutcome:
    email: str
    outcome: str
    invitation: WorkspaceInvitation | None


def create_invitations(
    actor: User, workspace_id, emails: list[str]
) -> list[InvitationOutcome]:
    """Invite one or several Google accounts. Duplicates (by mailbox) are reported, not errors."""
    membership = access.require_permission(
        actor, workspace_id, permissions.INVITATIONS_MANAGE
    )
    member_keys = {
        canonical_email_key(email)
        for email in WorkspaceMembership.objects.filter(
            workspace_id=workspace_id, status=MembershipStatus.ACTIVE
        ).values_list("user__email", flat=True)
    }
    now = timezone.now()
    results: list[InvitationOutcome] = []
    seen: set[str] = set()
    for email in emails:
        key = canonical_email_key(email)
        if key in seen:
            continue
        seen.add(key)
        if key in member_keys:
            results.append(InvitationOutcome(email, OUTCOME_ALREADY_MEMBER, None))
            continue
        open_invites = WorkspaceInvitation.objects.filter(
            workspace_id=workspace_id,
            email_key=key,
            accepted_at__isnull=True,
            closed_at__isnull=True,
        )
        existing = open_invites.filter(expires_at__gt=now).first()
        if existing:
            results.append(InvitationOutcome(email, OUTCOME_ALREADY_INVITED, existing))
            continue
        open_invites.update(closed_at=now)  # expired leftovers free the slot
        try:
            with transaction.atomic():
                invitation = WorkspaceInvitation.objects.create(
                    workspace_id=workspace_id,
                    email=email,
                    email_key=key,
                    invited_by=actor,
                    expires_at=now + INVITATION_EXPIRY,
                )
        except IntegrityError:  # concurrent duplicate request
            existing = open_invites.first()
            results.append(InvitationOutcome(email, OUTCOME_ALREADY_INVITED, existing))
            continue
        results.append(InvitationOutcome(email, OUTCOME_CREATED, invitation))
    created = sum(r.outcome == OUTCOME_CREATED for r in results)
    if created:
        hooks.emit(
            membership.workspace, actor, hooks.ACTION_INVITATION_CREATED, count=created
        )
    return results


def list_workspace_invitations(
    user: User, workspace_id
) -> QuerySet[WorkspaceInvitation]:
    access.require_permission(user, workspace_id, permissions.INVITATIONS_MANAGE)
    return WorkspaceInvitation.objects.filter(
        workspace_id=workspace_id,
        accepted_at__isnull=True,
        closed_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).order_by("-created_at", "id")


def revoke_invitation(user: User, workspace_id, invitation_id) -> None:
    membership = access.require_permission(
        user, workspace_id, permissions.INVITATIONS_MANAGE
    )
    updated = WorkspaceInvitation.objects.filter(
        pk=invitation_id,
        workspace_id=workspace_id,
        accepted_at__isnull=True,
        closed_at__isnull=True,
    ).update(closed_at=timezone.now())
    if not updated:
        raise NotFoundException(messages.MESSAGE_INVITATION_NOT_FOUND)
    hooks.emit(membership.workspace, user, hooks.ACTION_INVITATION_REVOKED)


def list_my_invitations(user: User) -> QuerySet[WorkspaceInvitation]:
    """Open invitations addressed to the mailbox the user signed in with."""
    return (
        WorkspaceInvitation.objects.select_related("workspace")
        .filter(
            email_key=canonical_email_key(user.email),
            accepted_at__isnull=True,
            closed_at__isnull=True,
            expires_at__gt=timezone.now(),
            workspace__is_deleted=False,
        )
        .order_by("-created_at", "id")
    )


def _get_my_invitation(user: User, invitation_id) -> WorkspaceInvitation:
    invitation = (
        WorkspaceInvitation.objects.select_related("workspace")
        .filter(pk=invitation_id, email_key=canonical_email_key(user.email))
        .first()
    )
    if invitation is None or invitation.workspace.is_deleted:
        raise NotFoundException(messages.MESSAGE_INVITATION_NOT_FOUND)
    return invitation


def accept_invitation(user: User, invitation_id) -> WorkspaceMembership:
    invitation = _get_my_invitation(user, invitation_id)
    if not invitation.is_usable():
        raise ConflictException(
            messages.MESSAGE_INVITATION_NOT_USABLE,
            error_code=errors.ERROR_INVITATION_NOT_USABLE,
        )
    with transaction.atomic():
        claimed = WorkspaceInvitation.objects.filter(
            pk=invitation.pk, accepted_at__isnull=True, closed_at__isnull=True
        ).update(accepted_at=timezone.now())
        if not claimed:  # accepted/closed by a concurrent request
            raise ConflictException(
                messages.MESSAGE_INVITATION_NOT_USABLE,
                error_code=errors.ERROR_INVITATION_NOT_USABLE,
            )
        membership, _ = member_service.add_member(invitation.workspace, user)
    hooks.emit(invitation.workspace, user, hooks.ACTION_INVITATION_ACCEPTED)
    return membership


def decline_invitation(user: User, invitation_id) -> None:
    invitation = _get_my_invitation(user, invitation_id)
    if not invitation.is_usable():
        raise ConflictException(
            messages.MESSAGE_INVITATION_NOT_USABLE,
            error_code=errors.ERROR_INVITATION_NOT_USABLE,
        )
    WorkspaceInvitation.objects.filter(pk=invitation.pk).update(
        closed_at=timezone.now()
    )
    hooks.emit(invitation.workspace, user, hooks.ACTION_INVITATION_DECLINED)
