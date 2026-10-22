"""Subscribers: every feature's hook signal feeds the audit log.

Each handler only translates a hook payload into `recorder.record`; which actions are kept,
and what they point at, is decided in `constants/actions.py`."""

from django.dispatch import receiver

from accounts.services import hooks as account_hooks
from ai.services import hooks as ai_hooks
from audit.constants.actions import ACTIONS
from audit.services import recorder
from email_integration.services import hooks as email_hooks
from knowledge.services import hooks as knowledge_hooks
from tickets.services import hooks as ticket_hooks
from workspaces.services import hooks as workspace_hooks


def _target(spec, workspace, actor, metadata: dict) -> tuple[str, str]:
    if spec.target_key and metadata.get(spec.target_key):
        return spec.target_type, str(metadata[spec.target_key])
    if spec.default_target == "workspace" and workspace is not None:
        return spec.target_type, str(workspace.id)
    if spec.default_target == "actor" and getattr(actor, "pk", None):
        return spec.target_type, str(actor.pk)
    return spec.target_type, ""


def _record(action: str, actor, workspace, metadata: dict) -> None:
    spec = ACTIONS.get(action)
    if spec is None:
        return
    metadata = dict(metadata or {})
    target_type, target_id = _target(spec, workspace, actor, metadata)
    for key in ("target_id",):
        metadata.pop(key, None)  # carried in the target columns instead
    recorder.record(
        action=action,
        actor=actor,
        workspace=None if spec.account_level else workspace,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata,
    )


@receiver(workspace_hooks.workspace_event)
def on_workspace_event(sender, workspace, actor, action, metadata, **kwargs) -> None:
    _record(
        action, actor, workspace, metadata
    )  # `workspace.purged` is not registered: its rows go with it


@receiver(knowledge_hooks.knowledge_event)
def on_knowledge_event(sender, workspace, actor, action, metadata, **kwargs) -> None:
    _record(action, actor, workspace, metadata)


@receiver(ticket_hooks.ticket_signal)
def on_ticket_event(
    sender, workspace_id, ticket_id, actor, action, metadata, **kwargs
) -> None:
    from workspaces.models import Workspace

    spec = ACTIONS.get(action)
    if spec is None:  # reply and note content stays in the ticket's own history
        return
    workspace = Workspace.all_objects.filter(pk=workspace_id).first()
    recorder.record(
        action=action,
        actor=actor,
        workspace=workspace,
        target_type=spec.target_type,
        target_id=str(ticket_id),
        metadata=metadata,
    )


@receiver(account_hooks.account_event)
def on_account_event(sender, user, action, metadata, **kwargs) -> None:
    _record(action, user, None, metadata)


@receiver(email_hooks.email_event)
def on_email_event(sender, user, action, metadata, **kwargs) -> None:
    _record(action, user, None, metadata)


@receiver(ai_hooks.ai_event)
def on_ai_event(sender, workspace, actor, action, metadata, **kwargs) -> None:
    _record(action, actor, workspace, metadata)
