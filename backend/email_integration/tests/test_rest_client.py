import base64
from unittest import mock

from django.test import SimpleTestCase, override_settings

from email_integration.clients.base import (
    GmailAuthError,
    GmailRejectedError,
    GmailTransientError,
)
from email_integration.clients.rest import RestGmailClient


def response(status=200, payload=None):
    r = mock.Mock()
    r.status_code = status
    r.content = b"x" if payload is not None else b""
    r.json.return_value = payload or {}
    return r


@override_settings(GOOGLE_CLIENT_ID="cid", GOOGLE_CLIENT_SECRET="secret")
class RestClientTests(SimpleTestCase):
    def make_client(self, *api_responses, token_response=None):
        client = RestGmailClient("refresh-1")
        client._session = mock.Mock()
        client._session.post.return_value = token_response or response(
            200, {"access_token": "access-1"}
        )
        client._session.request.side_effect = list(api_responses)
        return client

    def test_refresh_uses_the_client_credentials_and_bearer_token(self):
        client = self.make_client(response(200, {"historyId": "42"}))
        self.assertEqual(client.current_history_id(), "42")
        data = client._session.post.call_args.kwargs["data"]
        self.assertEqual(
            (data["grant_type"], data["refresh_token"], data["client_id"]),
            ("refresh_token", "refresh-1", "cid"),
        )
        self.assertEqual(
            client._session.request.call_args.kwargs["headers"],
            {"Authorization": "Bearer access-1"},
        )

    def test_revoked_refresh_token_is_an_auth_error(self):
        client = self.make_client(
            token_response=response(400, {"error": "invalid_grant"})
        )
        with self.assertRaises(GmailAuthError):
            client.current_history_id()

    def test_expired_access_token_is_refreshed_once(self):
        client = self.make_client(response(401), response(200, {"historyId": "7"}))
        self.assertEqual(client.current_history_id(), "7")
        self.assertEqual(client._session.post.call_count, 2)

    def test_error_classes(self):
        for status, error in (
            (403, GmailAuthError),
            (429, GmailTransientError),
            (503, GmailTransientError),
            (400, GmailRejectedError),
        ):
            client = self.make_client(response(status))
            with self.assertRaises(error, msg=status):
                client.list_inbox(5)

    def test_send_posts_urlsafe_base64_and_thread_id(self):
        client = self.make_client(response(200, {"id": "m1", "threadId": "t1"}))
        sent = client.send(b"Subject: hi\r\n\r\nbody", "t0")
        body = client._session.request.call_args.kwargs["json"]
        self.assertEqual(
            base64.urlsafe_b64decode(body["raw"]), b"Subject: hi\r\n\r\nbody"
        )
        self.assertEqual(
            (body["threadId"], sent.id, sent.thread_id), ("t0", "m1", "t1")
        )

    def test_get_message_parses_headers_body_and_date(self):
        text = base64.urlsafe_b64encode(b"Hello there").decode()
        payload = {
            "id": "m1",
            "threadId": "t1",
            "labelIds": ["INBOX"],
            "snippet": "Hello",
            "internalDate": "1792000000000",
            "payload": {
                "mimeType": "multipart/alternative",
                "headers": [
                    {"name": "Message-ID", "value": "<a@x.com>"},
                    {"name": "In-Reply-To", "value": "<b@x.com>"},
                    {"name": "X-Secret", "value": "ignored"},
                ],
                "parts": [{"mimeType": "text/plain", "body": {"data": text}}],
            },
        }
        message = self.make_client(response(200, payload)).get_message("m1")
        self.assertEqual(
            message.headers, {"message-id": "<a@x.com>", "in-reply-to": "<b@x.com>"}
        )
        self.assertEqual(
            (message.body_text, message.label_ids, message.thread_id),
            ("Hello there", ("INBOX",), "t1"),
        )

    def test_history_pages_are_merged_and_deduplicated(self):
        page1 = {
            "history": [{"messagesAdded": [{"message": {"id": "a"}}]}],
            "nextPageToken": "n",
            "historyId": "10",
        }
        page2 = {
            "history": [
                {"messagesAdded": [{"message": {"id": "b"}}, {"message": {"id": "a"}}]}
            ],
            "historyId": "12",
        }
        result = self.make_client(
            response(200, page1), response(200, page2)
        ).list_history("5")
        self.assertEqual((result.message_ids, result.history_id), (["a", "b"], "12"))

    def test_old_history_checkpoint_is_reported(self):
        with self.assertRaises(GmailRejectedError):
            self.make_client(response(404)).list_history("1")

    def test_watch_reads_the_expiration(self):
        result = self.make_client(
            response(200, {"historyId": "9", "expiration": "1792000000000"})
        ).watch("projects/p/topics/t")
        self.assertEqual((result.history_id, result.expires_at.year), ("9", 2026))
