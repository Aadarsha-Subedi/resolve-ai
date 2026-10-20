"""The Gmail API as our code needs it. Concrete clients: RestGmailClient (production) and
FakeGmailClient (tests). Services depend on this interface only."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


class GmailError(Exception):
    """Base class for Gmail failures."""


class GmailAuthError(GmailError):
    """The refresh token no longer works (revoked, expired, scope removed)."""


class GmailTransientError(GmailError):
    """Worth retrying: network trouble, 429, 5xx."""


class GmailRejectedError(GmailError):
    """Gmail refused this request (bad recipient, too large, ...). Retrying will not help."""


@dataclass(frozen=True)
class GmailMessage:
    id: str
    thread_id: str
    label_ids: tuple[str, ...]
    headers: dict[str, str]  # lower-cased header names
    body_text: str
    snippet: str
    received_at: datetime


@dataclass(frozen=True)
class SentMessage:
    id: str
    thread_id: str


@dataclass(frozen=True)
class HistoryResult:
    message_ids: list[str] = field(default_factory=list)
    history_id: str = ""


@dataclass(frozen=True)
class WatchResult:
    history_id: str
    expires_at: datetime


class GmailClient(ABC):
    @abstractmethod
    def send(self, raw_message: bytes, thread_id: str | None = None) -> SentMessage:
        """Send an RFC 822 message (keeps it in `thread_id` when given)."""

    @abstractmethod
    def get_message(self, message_id: str) -> GmailMessage:
        """Headers and plain-text body of one message."""

    @abstractmethod
    def list_inbox(self, limit: int) -> list[str]:
        """Ids of the newest `limit` inbox messages."""

    @abstractmethod
    def list_history(self, start_history_id: str) -> HistoryResult:
        """Ids of inbox messages added after `start_history_id` (raises
        GmailRejectedError if that checkpoint is too old)."""

    @abstractmethod
    def current_history_id(self) -> str:
        """The mailbox's current history position."""

    @abstractmethod
    def watch(self, topic: str) -> WatchResult:
        """Ask Gmail to publish inbox changes to a Pub/Sub topic."""

    @abstractmethod
    def stop_watch(self) -> None: ...

    @abstractmethod
    def revoke(self) -> None:
        """Revoke the grant at Google."""
