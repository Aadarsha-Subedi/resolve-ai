"""Gmail over plain HTTPS (requests). No Google client library is needed for these calls."""

import base64
import logging
from datetime import UTC, datetime, timedelta

import requests
from django.conf import settings
from django.utils import timezone

from email_integration.clients.base import (
    GmailAuthError,
    GmailClient,
    GmailError,
    GmailMessage,
    GmailRejectedError,
    GmailTransientError,
    HistoryResult,
    SentMessage,
    WatchResult,
)
from email_integration.constants import settings as cfg
from email_integration.services import parsing

logger = logging.getLogger(__name__)
_HEADERS_WANTED = (
    "message-id",
    "in-reply-to",
    "references",
    "from",
    "to",
    "subject",
    "date",
)


class RestGmailClient(GmailClient):
    def __init__(self, refresh_token: str) -> None:
        self._refresh_token = refresh_token
        self._access_token: str | None = None
        self._session = requests.Session()

    # -- auth -----------------------------------------------------------------

    def _refresh_access_token(self) -> str:
        try:
            response = self._session.post(
                cfg.TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                },
                timeout=cfg.HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise GmailTransientError("token endpoint unreachable") from exc
        if response.status_code in (400, 401):  # invalid_grant: revoked or expired
            raise GmailAuthError("refresh token rejected")
        if response.status_code != 200:
            raise GmailTransientError(f"token endpoint returned {response.status_code}")
        self._access_token = response.json()["access_token"]
        return self._access_token

    def _request(self, method: str, path: str, **kwargs) -> dict:
        for attempt in (1, 2):
            token = self._access_token or self._refresh_access_token()
            try:
                response = self._session.request(
                    method,
                    f"{cfg.GMAIL_API}{path}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=cfg.HTTP_TIMEOUT_SECONDS,
                    **kwargs,
                )
            except requests.RequestException as exc:
                raise GmailTransientError("gmail unreachable") from exc
            if response.status_code == 401 and attempt == 1:
                self._access_token = None  # expired: refresh once and retry
                continue
            return self._check(response)
        raise GmailAuthError("access token rejected")

    @staticmethod
    def _check(response: requests.Response) -> dict:
        detail = _reason(response)
        if response.status_code in (401, 403):
            raise GmailAuthError(f"gmail returned {response.status_code}{detail}")
        if response.status_code == 429 or response.status_code >= 500:
            raise GmailTransientError(f"gmail returned {response.status_code}{detail}")
        if response.status_code >= 400:
            raise GmailRejectedError(f"gmail returned {response.status_code}{detail}")
        return response.json() if response.content else {}

    # -- GmailClient ------------------------------------------------------------

    def send(self, raw_message: bytes, thread_id: str | None = None) -> SentMessage:
        body: dict = {"raw": base64.urlsafe_b64encode(raw_message).decode()}
        if thread_id:
            body["threadId"] = thread_id
        data = self._request("POST", "/messages/send", json=body)
        return SentMessage(id=data["id"], thread_id=data.get("threadId", ""))

    def get_message(self, message_id: str) -> GmailMessage:
        data = self._request(
            "GET", f"/messages/{message_id}", params={"format": "full"}
        )
        payload = data.get("payload", {})
        headers = {
            h["name"].lower(): h["value"]
            for h in payload.get("headers", [])
            if h["name"].lower() in _HEADERS_WANTED
        }
        received = datetime.fromtimestamp(
            int(data.get("internalDate", "0")) / 1000, tz=UTC
        )
        return GmailMessage(
            id=data["id"],
            thread_id=data.get("threadId", ""),
            label_ids=tuple(data.get("labelIds", [])),
            headers=headers,
            body_text=parsing.extract_text(payload),
            snippet=data.get("snippet", ""),
            received_at=received,
        )

    def list_inbox(self, limit: int) -> list[str]:
        data = self._request(
            "GET", "/messages", params={"labelIds": "INBOX", "maxResults": limit}
        )
        return [m["id"] for m in data.get("messages", [])]

    def list_history(self, start_history_id: str) -> HistoryResult:
        ids: list[str] = []
        page_token = None
        latest = start_history_id
        while True:
            params = {
                "startHistoryId": start_history_id,
                "historyTypes": "messageAdded",
                "labelId": "INBOX",
            }
            if page_token:
                params["pageToken"] = page_token
            try:
                data = self._request("GET", "/history", params=params)
            except GmailRejectedError as exc:  # 404: checkpoint too old
                raise GmailRejectedError("history checkpoint expired") from exc
            for record in data.get("history", []):
                ids.extend(m["message"]["id"] for m in record.get("messagesAdded", []))
            latest = data.get("historyId", latest)
            page_token = data.get("nextPageToken")
            if not page_token:
                return HistoryResult(
                    message_ids=list(dict.fromkeys(ids)), history_id=latest
                )

    def current_history_id(self) -> str:
        return str(self._request("GET", "/profile")["historyId"])

    def watch(self, topic: str) -> WatchResult:
        data = self._request(
            "POST", "/watch", json={"topicName": topic, "labelIds": ["INBOX"]}
        )
        expires = datetime.fromtimestamp(int(data["expiration"]) / 1000, tz=UTC)
        return WatchResult(history_id=str(data["historyId"]), expires_at=expires)

    def stop_watch(self) -> None:
        self._request("POST", "/stop")

    def revoke(self) -> None:
        try:
            self._session.post(
                cfg.REVOKE_URL,
                data={"token": self._refresh_token},
                timeout=cfg.HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise GmailError("revoke failed") from exc


def _reason(response: requests.Response) -> str:
    """Google's own error text (for example which Pub/Sub permission is missing), bounded.
    It never contains our tokens; it is only used in exception messages and logs."""
    try:
        message = response.json()["error"]["message"]
    except ValueError, KeyError, TypeError:
        return ""
    return f": {str(message)[:200]}"


def default_watch_deadline() -> datetime:
    return timezone.now() + timedelta(days=7)
