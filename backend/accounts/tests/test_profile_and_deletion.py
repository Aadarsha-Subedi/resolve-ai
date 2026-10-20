import logging
from datetime import timedelta
from unittest import mock

from allauth.usersessions.models import UserSession
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from accounts.services import hooks
from accounts.tasks import clear_expired_sessions, purge_deleted_accounts
from accounts.tests.base import OAUTH_CODE, AccountsTestCase
from common.throttling.scoped import AuthScopedThrottle


class ProfileTests(AccountsTestCase):
    def test_get_profile(self):
        client = self.login_client()
        response = client.get("/api/me/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["email"], "jane@example.com")
        self.assertEqual(data["display_name"], "Jane Doe")
        self.assertEqual(
            set(data), {"id", "email", "display_name", "avatar_url", "created_at"}
        )

    def test_patch_display_name_trims(self):
        client = self.login_client()
        response = client.patch("/api/me/", {"display_name": "  Jay  "}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get().display_name, "Jay")

    def test_patch_validation(self):
        client = self.login_client()
        for body in (
            {"display_name": ""},
            {"display_name": "   "},
            {"display_name": "x" * 81},
            {"display_name": "ok", "email": "a@b.com"},  # unknown field
            {"email": "a@b.com"},
        ):
            response = client.patch("/api/me/", body, format="json")
            self.assertEqual(response.status_code, 400, body)
        self.assertEqual(User.objects.get().email, "jane@example.com")


class DeletionTests(AccountsTestCase):
    def test_request_deletion_ends_sessions_and_sets_timestamp(self):
        a = self.login_client(ip="10.0.0.1")
        b = self.login_client(ip="10.0.0.2")
        a.get("/api/me/")
        b.get("/api/me/")
        response = a.delete("/api/me/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(User.objects.get().deletion_requested_at)
        self.assertIn(a.get("/api/me/").status_code, (401, 403))
        self.assertIn(b.get("/api/me/").status_code, (401, 403))
        self.assertFalse(UserSession.objects.exists())

    def test_visible_manager_hides_pending_deletion(self):
        client = self.login_client()
        client.delete("/api/me/")
        self.assertEqual(User.visible.count(), 0)
        self.assertEqual(User.objects.count(), 1)

    def test_blocked_by_ownership_check(self):
        client = self.login_client()
        check = mock.Mock(return_value="Owns workspace Acme.")
        with mock.patch.object(hooks, "ownership_checks", [check]):
            response = client.delete("/api/me/")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "account_owns_workspace")
        self.assertEqual(response.data["errors"][0]["message"], "Owns workspace Acme.")
        self.assertIsNone(User.objects.get().deletion_requested_at)
        self.assertEqual(client.get("/api/me/").status_code, 200)

    def test_passing_ownership_check_allows_deletion(self):
        client = self.login_client()
        with mock.patch.object(hooks, "ownership_checks", [lambda user: None]):
            self.assertEqual(client.delete("/api/me/").status_code, 200)

    def test_register_ownership_check_is_idempotent(self):
        with mock.patch.object(hooks, "ownership_checks", []):
            check = lambda user: None
            hooks.register_ownership_check(check)
            hooks.register_ownership_check(check)
            self.assertEqual(hooks.ownership_checks, [check])

    def test_delete_is_throttled(self):
        client = self.login_client()
        patched = {**AuthScopedThrottle.THROTTLE_RATES, "account_delete": "1/hour"}
        with (
            mock.patch.object(AuthScopedThrottle, "THROTTLE_RATES", patched),
            mock.patch.object(hooks, "ownership_checks", [lambda u: "blocked"]),
        ):
            self.assertEqual(client.delete("/api/me/").status_code, 409)
            self.assertEqual(client.delete("/api/me/").status_code, 429)

    def test_purge_task_deletes_only_after_grace(self):
        old = self.make_user(email="old@example.com")
        recent = self.make_user(email="recent@example.com")
        active = self.make_user(email="active@example.com")
        now = timezone.now()
        User.objects.filter(pk=old.pk).update(
            deletion_requested_at=now - timedelta(days=7, minutes=1)
        )
        User.objects.filter(pk=recent.pk).update(
            deletion_requested_at=now - timedelta(days=6)
        )
        self.assertEqual(purge_deleted_accounts(), 1)
        self.assertEqual(
            set(User.objects.values_list("email", flat=True)),
            {recent.email, active.email},
        )

    def test_audit_events_are_emitted(self):
        events = []
        hooks.account_event.connect(
            lambda sender, user, action, metadata, **kw: events.append(action),
            weak=False,
            dispatch_uid="test-collector",
        )
        self.addCleanup(hooks.account_event.disconnect, dispatch_uid="test-collector")
        client = self.login_client()
        client.patch("/api/me/", {"display_name": "Z"}, format="json")
        client.delete("/api/me/")
        self.assertEqual(
            events,
            [
                hooks.ACTION_LOGIN,
                hooks.ACTION_PROFILE_UPDATED,
                hooks.ACTION_DELETION_REQUESTED,
            ],
        )

    def test_clear_expired_sessions_task_removes_dead_device_rows(self):
        client = self.login_client()
        client.get("/api/me/")
        self.assertEqual(UserSession.objects.count(), 1)
        cache.clear()
        from django.contrib.sessions.models import Session

        Session.objects.all().delete()
        self.assertEqual(clear_expired_sessions(), 1)
        self.assertEqual(UserSession.objects.count(), 0)


class SecretLeakTests(AccountsTestCase):
    def test_no_tokens_or_secrets_in_logs(self):
        client = APIClient()
        with self.assertLogs("request", level=logging.INFO) as captured:
            self.sign_in(client=client)
            client.get("/api/me/")
        text = "\n".join(str(r.__dict__) for r in captured.records)
        self.assertNotIn(OAUTH_CODE, text)  # single-use Google code in the query
        self.assertNotIn("fake", text)  # the mocked access token
        self.assertNotIn(client.cookies["sessionid"].value, text)
        self.assertIn("REDACTED", text)

    def test_no_tokens_in_responses(self):
        client = self.login_client()
        for path in ("/api/me/", "/api/auth/sessions/"):
            body = client.get(path).content.decode()
            self.assertNotIn("fake", body)
            self.assertNotIn(client.cookies["sessionid"].value, body)
