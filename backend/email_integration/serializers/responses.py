from dataclasses import dataclass

from django.utils import timezone

from common.response.domain import BaseResponseData
from email_integration.constants import settings as cfg
from email_integration.constants.enums import ConnectionStatus
from email_integration.models import GmailConnection, UnmatchedEmail

RECONNECT_PATH = "/api/auth/google/start/?reconnect=1"


@dataclass(frozen=True)
class ConnectionData(BaseResponseData):
    connection: GmailConnection | None

    def to_dict(self) -> dict:
        c = self.connection
        if c is None:
            return {
                "status": ConnectionStatus.NOT_CONNECTED,
                "reconnect_path": RECONNECT_PATH,
            }
        needs_signin = c.status != ConnectionStatus.CONNECTED
        return {
            "status": c.status,
            "mailbox_email": c.mailbox_email,
            "has_required_scopes": cfg.REQUIRED_SCOPES <= set(c.granted_scopes),
            "connected_at": c.connected_at.isoformat() if c.connected_at else None,
            "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            "push_active": bool(
                c.watch_expires_at and c.watch_expires_at > timezone.now()
            ),
            # Tokens are never part of any response.
            "reconnect_path": RECONNECT_PATH if needs_signin else None,
        }


@dataclass(frozen=True)
class ReviewItemData(BaseResponseData):
    item: UnmatchedEmail

    def to_dict(self) -> dict:
        i = self.item
        return {
            "id": str(i.id),
            "sender_email": i.sender_email,
            "sender_name": i.sender_name,
            "subject": i.subject,
            "snippet": i.snippet,
            "received_at": i.received_at.isoformat(),
        }


@dataclass(frozen=True)
class DictData(BaseResponseData):
    payload: dict

    def to_dict(self) -> dict:
        return self.payload
