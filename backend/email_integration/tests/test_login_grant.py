from unittest import mock
from urllib.parse import parse_qs, urlsplit

from django.db import connection as db_connection
from rest_framework.test import APIClient

from accounts.models import User
from accounts.tests.base import START, AccountsTestCase
from email_integration.constants.enums import ConnectionStatus
from email_integration.constants.settings import REQUIRED_SCOPES, SCOPE_READ
from email_integration.models import GmailConnection
from email_integration.services import token_service


class LoginGrantTests(AccountsTestCase):
    def grant(self, scopes):
        return mock.patch(
            "email_integration.services.connection_service.fetch_granted_scopes",
            return_value=set(scopes),
        )

    def login(self, refresh="refresh-abc", scopes=REQUIRED_SCOPES, **kw):
        data = {"access_token": "access-1"}
        if refresh:
            data["refresh_token"] = refresh
        with self.grant(scopes):
            return self.sign_in(token_data=data, **kw)

    def test_sign_in_redirect_asks_for_gmail_and_offline_access(self):
        query = parse_qs(urlsplit(self.client.get(START)["Location"]).query)
        scopes = query["scope"][0].split()
        self.assertEqual(
            set(scopes),
            {"openid", "email", "profile", *REQUIRED_SCOPES},
        )
        self.assertEqual(query["access_type"], ["offline"])
        self.assertEqual(query["prompt"], ["select_account"])

    def test_reconnect_forces_the_consent_screen_and_ignores_caller_scopes(self):
        query = parse_qs(
            urlsplit(
                self.client.get(
                    START + "?reconnect=1&scope=drive&auth_params=prompt%3Dnone"
                )["Location"]
            ).query
        )
        self.assertEqual(query["prompt"], ["consent"])
        self.assertNotIn("drive", query["scope"][0])

    def test_signed_in_user_can_reconnect(self):
        self.login()
        response = self.client.get(START + "?reconnect=1")
        self.assertIn("accounts.google.com", response["Location"])
        plain = self.client.get(
            START
        )  # without reconnect a signed-in user goes to the app
        self.assertNotIn("accounts.google.com", plain["Location"])

    def test_refresh_token_is_stored_encrypted_only(self):
        self.login(refresh="super-secret-refresh-token")
        connection = GmailConnection.objects.get()
        self.assertEqual(connection.status, ConnectionStatus.CONNECTED)
        self.assertNotIn("super-secret", connection.encrypted_refresh_token)
        self.assertEqual(
            token_service.decrypt_refresh_token(connection),
            "super-secret-refresh-token",
        )
        with db_connection.cursor() as cursor:
            cursor.execute("select * from email_gmail_connection")
            row = str(cursor.fetchall())
        self.assertNotIn("super-secret", row)
        self.assertEqual(connection.mailbox_email, "jane@example.com")
        self.assertEqual(connection.user, User.objects.get())

    def test_status_endpoint_never_returns_tokens(self):
        self.login(refresh="super-secret-refresh-token")
        body = self.client.get("/api/email/gmail/").content.decode()
        for secret in ("super-secret", "access-1", "encrypted"):
            self.assertNotIn(secret, body)
        data = self.client.get("/api/email/gmail/").data["data"]
        self.assertEqual(
            (data["status"], data["has_required_scopes"], data["reconnect_path"]),
            ("connected", True, None),
        )

    def test_declined_gmail_scopes_still_log_in_but_not_connected(self):
        response = self.login(scopes={"openid", "email", "profile"})
        self.assertEqual(response.status_code, 302)
        connection = GmailConnection.objects.get()
        self.assertEqual(
            (connection.status, connection.encrypted_refresh_token),
            (ConnectionStatus.NOT_CONNECTED, ""),
        )
        status = self.client.get("/api/email/gmail/").data["data"]
        self.assertEqual(
            (status["status"], status["has_required_scopes"]), ("not_connected", False)
        )
        self.assertIn("reconnect=1", status["reconnect_path"])

    def test_only_one_of_two_scopes_is_not_enough(self):
        self.login(scopes={SCOPE_READ})
        self.assertEqual(
            GmailConnection.objects.get().status, ConnectionStatus.NOT_CONNECTED
        )

    def test_later_login_without_refresh_token_keeps_the_stored_one(self):
        self.login(refresh="first-refresh")
        self.login(refresh=None, client=APIClient())
        connection = GmailConnection.objects.get()
        self.assertEqual(connection.status, ConnectionStatus.CONNECTED)
        self.assertEqual(
            token_service.decrypt_refresh_token(connection), "first-refresh"
        )

    def test_first_login_without_refresh_token_is_not_connected(self):
        self.login(refresh=None)
        self.assertEqual(
            GmailConnection.objects.get().status, ConnectionStatus.NOT_CONNECTED
        )

    def test_new_refresh_token_replaces_the_old_one_and_recovers_reauth(self):
        self.login(refresh="old")
        GmailConnection.objects.update(status=ConnectionStatus.REAUTH_REQUIRED)
        self.login(refresh="new", client=APIClient())
        connection = GmailConnection.objects.get()
        self.assertEqual(connection.status, ConnectionStatus.CONNECTED)
        self.assertEqual(token_service.decrypt_refresh_token(connection), "new")

    def test_google_failure_never_breaks_sign_in(self):
        with mock.patch(
            "email_integration.services.connection_service.token_service.encrypt_refresh_token",
            side_effect=RuntimeError("encryption down"),
        ):
            response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("google_error", response["Location"])
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

    def test_one_connection_per_user(self):
        self.login()
        self.login(client=APIClient())
        self.assertEqual(GmailConnection.objects.count(), 1)

    def test_disconnect_revokes_wipes_and_reports(self):
        from email_integration.clients.fake import FakeGmailClient

        self.login()
        fake = FakeGmailClient()
        with mock.patch(
            "email_integration.clients.get_gmail_client", return_value=fake
        ):
            response = self.client.delete("/api/email/gmail/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(fake.revoked)
        connection = GmailConnection.objects.get()
        self.assertEqual(
            (connection.status, connection.encrypted_refresh_token),
            (ConnectionStatus.DISCONNECTED, ""),
        )
        self.assertEqual(
            self.client.get("/api/email/gmail/").data["data"]["status"], "disconnected"
        )

    def test_status_requires_login(self):
        self.assertEqual(APIClient().get("/api/email/gmail/").status_code, 401)
        self.assertEqual(APIClient().delete("/api/email/gmail/").status_code, 401)
        self.assertEqual(APIClient().post("/api/email/gmail/sync/").status_code, 401)
