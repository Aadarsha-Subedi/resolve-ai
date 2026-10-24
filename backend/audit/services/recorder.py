import logging

from audit.constants import settings as cfg
from audit.constants.actions import ACTIONS
from audit.models import AuditEvent
from audit.services.sanitize import sanitize_metadata

logger = logging.getLogger(__name__)


def _actor_name(actor) -> str:
    if actor is None:
        return ""
    return (getattr(actor, "display_name", "") or getattr(actor, "email", ""))[
        : cfg.ACTOR_NAME_MAX_LENGTH
    ]


def record(
    *,
    action: str,
    actor=None,
    workspace=None,
    target_type: str = "",
    target_id: str = "",
    metadata: dict | None = None,
) -> AuditEvent | None:
    """Write one audit row. Never raises: a failing audit write must not break the action
    that was being audited (it is logged instead). Unregistered actions are ignored."""
    if action not in ACTIONS:
        logger.warning("Audit action %r is not registered", action)
        return None
    try:
        return AuditEvent.objects.create(
            workspace=workspace,
            actor_user=actor if getattr(actor, "pk", None) else None,
            actor_name=_actor_name(actor),
            action=action,
            target_type=target_type[: cfg.TARGET_TYPE_MAX_LENGTH],
            target_id=str(target_id)[: cfg.TARGET_ID_MAX_LENGTH],
            metadata=sanitize_metadata(metadata),
        )
    except Exception:
        logger.exception("Could not write the audit event %s", action)
        return None
