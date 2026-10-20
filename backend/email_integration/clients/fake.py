"""In-memory Gmail for tests. Inspect `sent`, add mail with `deliver`."""

import itertools
from datetime import UTC, datetime, timedelta

from email_integration.clients.base import (
    GmailAuthError,
    GmailClient,
    GmailMessage,
    GmailRejectedError,
    GmailTransientError,
    HistoryResult,
    SentMessage,
    WatchResult,
)


class FakeGmailClient(GmailClient):
    def __init__(self) -> None:
        self._ids = itertools.count(1)
        self.messages: dict[str, GmailMessage] = {}
        self.inbox: list[str] = []
        self.history: list[tuple[int, str]] = []  # (history id, message id)
        self.history_counter = 100
        self.sent: list[dict] = []
        self.watch_topics: list[str] = []
        self.revoked = False
        self.fail_with: Exception | None = None  # raised by the next call
        self.expired_history = False

    def _maybe_fail(self) -> None:
        if self.fail_with is not None:
            error, self.fail_with = self.fail_with, None
            raise error

    def deliver(
        self,
        *,
        sender="customer@example.com",
        subject="Re: hello",
        body="Thanks!",
        message_id=None,
        in_reply_to="",
        references="",
        labels=("INBOX",),
    ) -> str:
        """Put a message in the mailbox the way Gmail would after receiving it."""
        number = next(self._ids)
        gmail_id = f"g{number}"
        headers = {
            "message-id": message_id
            if message_id is not None
            else f"<in-{number}@mail.example>",
            "from": sender,
            "subject": subject,
            "in-reply-to": in_reply_to,
            "references": references,
        }
        self.messages[gmail_id] = GmailMessage(
            id=gmail_id,
            thread_id=f"t{number}",
            label_ids=tuple(labels),
            headers={k: v for k, v in headers.items() if v},
            body_text=body,
            snippet=body[:100],
            received_at=datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
            + timedelta(minutes=number),
        )
        if "INBOX" in labels:
            self.inbox.insert(0, gmail_id)
            self.history_counter += 1
            self.history.append((self.history_counter, gmail_id))
        return gmail_id

    # -- GmailClient --------------------------------------------------------------

    def send(self, raw_message: bytes, thread_id: str | None = None) -> SentMessage:
        self._maybe_fail()
        number = next(self._ids)
        gmail_id = f"s{number}"
        from email import message_from_bytes

        parsed = message_from_bytes(raw_message)
        self.sent.append(
            {
                "id": gmail_id,
                "thread_id": thread_id,
                "message": parsed,
                "raw": raw_message,
            }
        )
        # Gmail keeps (or replaces) the Message-ID; the fake keeps what was asked.
        self.messages[gmail_id] = GmailMessage(
            id=gmail_id,
            thread_id=thread_id or f"st{number}",
            label_ids=("SENT",),
            headers={
                "message-id": parsed["Message-ID"] or f"<sent-{number}@gmail.example>"
            },
            body_text="",
            snippet="",
            received_at=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
        )
        return SentMessage(id=gmail_id, thread_id=thread_id or f"st{number}")

    def get_message(self, message_id: str) -> GmailMessage:
        self._maybe_fail()
        return self.messages[message_id]

    def list_inbox(self, limit: int) -> list[str]:
        self._maybe_fail()
        return self.inbox[:limit]

    def list_history(self, start_history_id: str) -> HistoryResult:
        self._maybe_fail()
        if self.expired_history:
            raise GmailRejectedError("history checkpoint expired")
        start = int(start_history_id)
        ids = [m for h, m in self.history if h > start]
        return HistoryResult(message_ids=ids, history_id=str(self.history_counter))

    def current_history_id(self) -> str:
        self._maybe_fail()
        return str(self.history_counter)

    def watch(self, topic: str) -> WatchResult:
        self._maybe_fail()
        self.watch_topics.append(topic)
        return WatchResult(
            history_id=str(self.history_counter),
            expires_at=datetime(2026, 10, 27, tzinfo=UTC),
        )

    def stop_watch(self) -> None:
        self._maybe_fail()

    def revoke(self) -> None:
        self.revoked = True


__all__ = ["FakeGmailClient", "GmailAuthError", "GmailTransientError"]
