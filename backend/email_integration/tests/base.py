from unittest import mock

from cryptography.fernet import Fernet
from django.test import override_settings

from email_integration.clients.fake import FakeGmailClient
from email_integration.constants.enums import ConnectionStatus
from email_integration.constants.settings import REQUIRED_SCOPES
from email_integration.models import GmailConnection
from email_integration.services import token_service
from tickets.tests.base import TicketTestCase

KEY = Fernet.generate_key().decode()


# Whatever push settings the developer has in .env, tests start with push switched off.
@override_settings(
    ENCRYPTION_KEYS=[KEY],
    GMAIL_PUBSUB_TOPIC="",
    PUBSUB_PUSH_AUDIENCE="",
    PUBSUB_PUSH_SERVICE_ACCOUNT="",
)
class EmailTestCase(TicketTestCase):
    """Tickets workspace with a fake Gmail per user. Celery runs tasks inline and
    `api()` runs the after-commit hooks the way a real request would."""

    def setUp(self):
        super().setUp()
        self.fakes: dict = {}
        patcher = mock.patch(
            "email_integration.clients.get_gmail_client",
            side_effect=lambda connection: self.fakes.setdefault(
                connection.user_id, FakeGmailClient()
            ),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def connect(self, user, status=ConnectionStatus.CONNECTED) -> GmailConnection:
        connection, _ = GmailConnection.objects.update_or_create(
            user=user,
            defaults={
                "google_subject": f"sub-{user.id}",
                "mailbox_email": user.email,
                "encrypted_refresh_token": token_service.encrypt_refresh_token(
                    f"refresh-{user.id}"
                ),
                "granted_scopes": sorted(REQUIRED_SCOPES),
                "status": status,
            },
        )
        return connection

    def gmail(self, user) -> FakeGmailClient:
        return self.fakes.setdefault(user.id, FakeGmailClient())

    def api(self, client, method, url, body=None):
        with self.captureOnCommitCallbacks(execute=True):
            call = getattr(client, method)
            return call(url, body, format="json") if body is not None else call(url)

    def reply(self, ticket_id, body="We are on it.", client=None, visibility="public"):
        return self.api(
            client or self.member_client,
            "post",
            self.turl(f"{ticket_id}/messages/"),
            {"body": body, "visibility": visibility},
        )

    def message(self, ticket_id, index=-1):
        from tickets.models import TicketMessage

        return list(
            TicketMessage.objects.filter(ticket_id=ticket_id).order_by(
                "created_at", "id"
            )
        )[index]
