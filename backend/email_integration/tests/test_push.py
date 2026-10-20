import base64
import json
from unittest import mock

from django.test import override_settings
from rest_framework.test import APIClient

from email_integration.models import GmailConnection
from email_integration.tests.base import EmailTestCase

URL = "/api/email/gmail/push/"
SERVICE_ACCOUNT = "pubsub@project.iam.gserviceaccount.com"
AUDIENCE = "https://api.example.com/api/email/gmail/push/"


def notification(email="member@example.com", history_id="500"):
    data = base64.b64encode(
        json.dumps({"emailAddress": email, "historyId": history_id}).encode()
    ).decode()
    return {
        "message": {"data": data, "messageId": "1"},
        "subscription": "projects/p/subscriptions/s",
    }


def claims(**overrides):
    return {
        "iss": "https://accounts.google.com",
        "email": SERVICE_ACCOUNT,
        "email_verified": True,
        **overrides,
    }


@override_settings(
    PUBSUB_PUSH_AUDIENCE=AUDIENCE, PUBSUB_PUSH_SERVICE_ACCOUNT=SERVICE_ACCOUNT
)
class PushTests(EmailTestCase):
    def setUp(self):
        super().setUp()
        self.connection = self.connect(self.member)
        self.fake = self.gmail(self.member)
        self.client_anon = APIClient()

    def post(self, body=None, token="good", verify=None):
        verify = verify or mock.Mock(return_value=claims())
        with mock.patch(
            "email_integration.services.push_service.id_token.verify_oauth2_token",
            verify,
        ):
            headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
            return self.client_anon.post(
                URL,
                body if body is not None else notification(),
                format="json",
                **headers,
            )

    def test_valid_push_syncs_the_mailbox(self):
        ticket = self.new_ticket(customer_email="jane@example.com")
        self.reply(ticket["id"], "hi")
        sent = self.message(ticket["id"]).email_message_id
        GmailConnection.objects.update(history_id=str(self.fake.history_counter))
        self.fake.deliver(sender="jane@example.com", in_reply_to=sent)
        response = self.post()
        self.assertEqual(response.status_code, 200)
        from tickets.models import TicketMessage

        self.assertEqual(
            TicketMessage.objects.filter(
                ticket_id=ticket["id"], author_type="customer"
            ).count(),
            2,
        )

    def test_audience_is_checked(self):
        verify = mock.Mock(return_value=claims())
        self.post(verify=verify)
        self.assertEqual(verify.call_args.kwargs["audience"], AUDIENCE)

    def test_bad_credentials_are_rejected(self):
        for kwargs in (
            {"token": ""},
            {"verify": mock.Mock(side_effect=ValueError("bad"))},
            {"verify": mock.Mock(return_value=claims(email="attacker@evil.com"))},
            {"verify": mock.Mock(return_value=claims(email_verified=False))},
            {"verify": mock.Mock(return_value=claims(iss="https://evil.com"))},
        ):
            response = self.post(**kwargs)
            self.assertEqual(
                (response.status_code, response.data["code"]),
                (401, "push_unauthorized"),
                kwargs,
            )

    def test_no_session_is_needed_and_garbage_is_acknowledged(self):
        for body in (
            {},
            {"message": {}},
            {"message": {"data": "not-base64!"}},
            notification("nobody@example.org"),
        ):
            self.assertEqual(self.post(body).status_code, 200, body)

    def test_disconnected_mailboxes_are_not_synced(self):
        GmailConnection.objects.update(status="disconnected")
        with mock.patch("email_integration.views.gmail.sync_mailbox") as task:
            self.post()
        task.delay.assert_not_called()

    def test_push_disabled_without_configuration(self):
        with override_settings(PUBSUB_PUSH_AUDIENCE="", PUBSUB_PUSH_SERVICE_ACCOUNT=""):
            response = self.post()
        self.assertEqual(
            (response.status_code, response.data["code"]), (404, "push_disabled")
        )


class WatchTests(EmailTestCase):
    def test_watch_is_registered_when_a_topic_is_configured(self):
        from email_integration.services import connection_service

        connection = self.connect(self.member)
        with override_settings(GMAIL_PUBSUB_TOPIC="projects/p/topics/gmail"):
            connection_service.ensure_watch(connection)
        self.assertEqual(
            self.gmail(self.member).watch_topics, ["projects/p/topics/gmail"]
        )
        connection.refresh_from_db()
        self.assertIsNotNone(connection.watch_expires_at)
        self.assertTrue(connection.history_id)

    def test_no_topic_means_no_watch(self):
        from email_integration.services import connection_service

        connection_service.ensure_watch(self.connect(self.member))
        self.assertEqual(self.gmail(self.member).watch_topics, [])

    def test_watches_ending_soon_are_renewed(self):
        from datetime import timedelta

        from django.utils import timezone

        from email_integration.tasks import renew_gmail_watches

        soon, later = self.connect(self.member), self.connect(self.owner)
        GmailConnection.objects.filter(pk=soon.pk).update(
            watch_expires_at=timezone.now() + timedelta(hours=5)
        )
        GmailConnection.objects.filter(pk=later.pk).update(
            watch_expires_at=timezone.now() + timedelta(days=6)
        )
        with override_settings(GMAIL_PUBSUB_TOPIC="projects/p/topics/gmail"):
            self.assertEqual(renew_gmail_watches(), 1)
        self.assertEqual(len(self.gmail(self.member).watch_topics), 1)
        self.assertEqual(self.gmail(self.owner).watch_topics, [])
