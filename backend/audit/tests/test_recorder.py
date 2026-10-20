from unittest import mock

from django.test import SimpleTestCase, TestCase

from accounts.models import User
from audit.models import AuditEvent
from audit.services import recorder
from audit.services.sanitize import sanitize_metadata


class SanitizeTests(SimpleTestCase):
    def test_keeps_flat_facts(self):
        self.assertEqual(
            sanitize_metadata(
                {
                    "old": "open",
                    "new": "closed",
                    "count": 3,
                    "ok": True,
                    "none": None,
                    "fields": ["a", "b"],
                }
            ),
            {
                "old": "open",
                "new": "closed",
                "count": 3,
                "ok": True,
                "none": None,
                "fields": ["a", "b"],
            },
        )

    def test_drops_secrets_and_content_by_key(self):
        dirty = {
            "access_token": "t",
            "refresh_token": "r",
            "raw_token": "x",
            "password": "p",
            "client_secret": "s",
            "api_key": "k",
            "body": "hello",
            "body_text": "hello",
            "content": "c",
            "snippet": "s",
            "html": "<b>",
            "cookie": "c",
            "session_key": "k",
            "Authorization": "Bearer x",
            "signature": "sig",
            "kept": "fine",
            "message_id": "m1",
            "expires_in": "1h",
        }
        self.assertEqual(
            sanitize_metadata(dirty),
            {"kept": "fine", "message_id": "m1", "expires_in": "1h"},
        )

    def test_emails_are_masked_not_stored(self):
        clean = sanitize_metadata(
            {"invited": "jane@example.com", "list": ["a@b.com", "plain"]}
        )
        self.assertEqual(clean["invited"], "j***@example.com")
        self.assertEqual(clean["list"], ["a***@b.com", "plain"])
        self.assertNotIn("jane@example.com", str(clean))

    def test_nested_values_and_long_strings_are_bounded(self):
        clean = sanitize_metadata(
            {"nested": {"a": 1}, "deep": [{"a": 1}, "ok"], "long": "x" * 1000}
        )
        self.assertNotIn("nested", clean)
        self.assertEqual(clean["deep"], ["ok"])
        self.assertEqual(len(clean["long"]), 200)

    def test_huge_metadata_is_replaced_by_a_marker(self):
        big = {f"k{i}": "v" * 150 for i in range(40)}
        self.assertEqual(sanitize_metadata(big), {"truncated": True})

    def test_none_and_empty(self):
        self.assertEqual(sanitize_metadata(None), {})
        self.assertEqual(sanitize_metadata({}), {})

    def test_lists_are_capped(self):
        self.assertEqual(len(sanitize_metadata({"ids": list(range(100))})["ids"]), 20)


class RecorderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="a@example.com", display_name="Alice"
        )

    def test_records_with_an_actor_name_snapshot(self):
        event = recorder.record(
            action="deletion_requested",
            actor=self.user,
            target_type="user",
            target_id=self.user.pk,
        )
        self.assertEqual(
            (event.actor_name, event.actor_user, event.workspace),
            ("Alice", self.user, None),
        )
        self.assertEqual(event.target_id, str(self.user.pk))

    def test_unregistered_actions_are_ignored(self):
        self.assertIsNone(recorder.record(action="ticket.reply_added", actor=self.user))
        self.assertIsNone(recorder.record(action="made.up", actor=self.user))
        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_a_failing_write_never_raises(self):
        with (
            mock.patch.object(
                AuditEvent.objects, "create", side_effect=RuntimeError("db down")
            ),
            self.assertLogs("audit.services.recorder", level="ERROR"),
        ):
            self.assertIsNone(recorder.record(action="logout_all", actor=self.user))

    def test_secrets_in_metadata_never_reach_the_row(self):
        event = recorder.record(
            action="logout_all",
            actor=self.user,
            metadata={"refresh_token": "SECRET", "note": "ok"},
        )
        self.assertEqual(event.metadata, {"note": "ok"})
        self.assertNotIn("SECRET", str(AuditEvent.objects.values()))

    def test_events_are_append_only(self):
        event = recorder.record(action="logout_all", actor=self.user)
        event.action = "deleted"
        with self.assertRaises(RuntimeError):
            event.save()
        self.assertEqual(AuditEvent.objects.get().action, "logout_all")

    def test_the_log_outlives_the_actors_account(self):
        recorder.record(action="logout_all", actor=self.user)
        self.user.delete()
        event = AuditEvent.objects.get()
        self.assertEqual((event.actor_user, event.actor_name), (None, "Alice"))
