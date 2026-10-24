from dataclasses import dataclass

from audit.models import AuditEvent
from common.response.domain import BaseResponseData


@dataclass(frozen=True)
class AuditEventData(BaseResponseData):
    event: AuditEvent

    def to_dict(self) -> dict:
        e = self.event
        return {
            "id": str(e.id),
            "action": e.action,
            "actor": (
                {
                    "id": str(e.actor_user_id) if e.actor_user_id else None,
                    "name": e.actor_name,
                }
                if e.actor_name or e.actor_user_id
                else None
            ),
            "target": {"type": e.target_type, "id": e.target_id}
            if e.target_type
            else None,
            "metadata": e.metadata,
            "created_at": e.created_at.isoformat(),
        }
