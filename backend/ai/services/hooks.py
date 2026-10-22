"""Audit extension point (the audit app subscribes to `ai_event`).
Metadata never carries API keys or prompts."""

from django.dispatch import Signal

SENDER = "ai"
ai_event = Signal()  # kwargs: workspace, actor, action, metadata

ACTION_MODE_CHANGED = "llm.mode_changed"
ACTION_KEY_SAVED = "llm.key_saved"
ACTION_KEY_REMOVED = "llm.key_removed"


def emit(workspace, actor, action: str, **metadata) -> None:
    ai_event.send(
        sender=SENDER,
        workspace=workspace,
        actor=actor,
        action=action,
        metadata=metadata,
    )
