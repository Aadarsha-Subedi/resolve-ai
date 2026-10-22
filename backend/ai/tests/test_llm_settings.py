import json
from unittest import mock

from cryptography.fernet import Fernet
from django.test import override_settings

from ai.models import UserWorkspaceLLMSettings
from ai.services import key_vault, settings_service
from audit.models import AuditEvent
from common.llm import LLMInvalidKeyError, LLMTimeoutError, LLMUnavailableError
from common.llm.fake import FakeProvider
from workspaces.tests.base import WorkspaceTestCase

SECRET = "sk-test-SECRET-0123456789abcd"


@override_settings(
    ENCRYPTION_KEYS=[Fernet.generate_key().decode()], GEMINI_API_KEY="server-key"
)
class LLMSettingsTestCase(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        self.workspace_id = self.workspace_with_member()
        self.fake = FakeProvider()
        patcher = mock.patch(
            "ai.services.settings_service.create_provider", return_value=self.fake
        )
        self.create_provider = patcher.start()
        self.addCleanup(patcher.stop)

    def lurl(self, suffix="", workspace_id=None):
        return f"/api/workspaces/{workspace_id or self.workspace_id}/llm/{suffix}"

    def get(self, client=None):
        return (client or self.member_client).get(self.lurl())

    def patch(self, body, client=None):
        return (client or self.member_client).patch(self.lurl(), body, format="json")

    def save_key(self, client=None, provider="openai", **extra):
        return self.patch(
            {"own_provider": provider, "api_key": SECRET, **extra}, client
        )

    def row(self, user=None):
        return UserWorkspaceLLMSettings.objects.get(
            workspace_id=self.workspace_id, user=user or self.member
        )


class ReadSettingsTests(LLMSettingsTestCase):
    def test_defaults_when_nothing_is_saved(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["mode"], "resolve_ai")
        self.assertEqual(data["resolve_ai_model"], "gemini-3.5-flash-lite")
        self.assertEqual(data["own_key"]["has_key"], False)
        self.assertTrue(data["options"]["resolve_ai"]["available"])
        self.assertIn("gpt-5-mini", data["options"]["providers"]["openai"]["models"])
        self.assertFalse(UserWorkspaceLLMSettings.objects.exists())

    def test_non_members_get_404_and_anonymous_is_refused(self):
        self.assertEqual(self.get(self.stranger_client).status_code, 404)
        self.assertEqual(
            self.patch({"mode": "resolve_ai"}, self.stranger_client).status_code, 404
        )
        from rest_framework.test import APIClient

        self.assertIn(APIClient().get(self.lurl()).status_code, (401, 403))

    def test_settings_are_private_to_each_user(self):
        self.save_key()
        owner_view = self.get(self.owner_client).data["data"]
        self.assertEqual(owner_view["own_key"]["has_key"], False)
        self.assertEqual(self.get().data["data"]["own_key"]["has_key"], True)


class SaveKeyTests(LLMSettingsTestCase):
    def test_key_is_checked_encrypted_and_never_returned(self):
        response = self.save_key()
        self.assertEqual(response.status_code, 200)
        own = response.data["data"]["own_key"]
        self.assertEqual(
            (own["has_key"], own["provider"], own["model"], own["last4"]),
            (True, "openai", "gpt-5-mini", SECRET[-4:]),
        )
        self.assertNotIn(SECRET, json.dumps(response.data, default=str))
        self.assertNotIn(SECRET, json.dumps(self.get().data, default=str))
        self.create_provider.assert_called_with("openai", SECRET, "gpt-5-mini")
        row = self.row()
        self.assertNotIn(SECRET, row.own_key_encrypted)
        self.assertEqual(
            key_vault.unseal(self.workspace_id, self.member.id, row.own_key_encrypted),
            SECRET,
        )
        self.assertIsNotNone(row.own_key_checked_at)
        self.assertEqual(row.mode, "resolve_ai")  # saving a key does not switch mode

    def test_rejected_key_is_not_saved(self):
        self.fake.key_valid = False
        response = self.save_key()
        self.assertEqual(
            (response.status_code, response.data["code"]), (400, "llm_invalid_key")
        )
        self.assertFalse(UserWorkspaceLLMSettings.objects.exists())

    def test_provider_outage_is_a_503_and_nothing_is_saved(self):
        for error in (LLMTimeoutError(), LLMUnavailableError()):
            self.fake.validate_key = mock.Mock(side_effect=error)
            response = self.save_key()
            self.assertEqual(
                (response.status_code, response.data["code"]), (503, error.code)
            )
        self.assertFalse(UserWorkspaceLLMSettings.objects.exists())

    def test_key_needs_a_provider_and_a_known_model(self):
        response = self.patch({"api_key": SECRET})
        self.assertEqual(
            (response.status_code, response.data["code"]),
            (400, "llm_provider_required"),
        )
        response = self.save_key(own_model="gpt-99")
        self.assertEqual(
            (response.status_code, response.data["code"]),
            (400, "llm_model_not_allowed"),
        )
        response = self.save_key(provider="gemini", own_model="gpt-5-mini")
        self.assertEqual(response.data["code"], "llm_model_not_allowed")
        self.assertFalse(UserWorkspaceLLMSettings.objects.exists())

    def test_bad_bodies_are_rejected(self):
        self.assertEqual(self.patch({}).status_code, 400)
        self.assertEqual(self.patch({"mode": "other"}).status_code, 400)
        self.assertEqual(self.patch({"own_provider": "anthropic"}).status_code, 400)
        self.assertEqual(self.patch({"api_key": "short"}).status_code, 400)
        self.assertEqual(self.patch({"api_key": "has a space inside"}).status_code, 400)
        self.assertEqual(self.patch({"surprise": 1}).status_code, 400)

    def test_replacing_a_key_updates_last4(self):
        self.save_key()
        self.patch({"own_provider": "openai", "api_key": "sk-another-key-9999"})
        self.assertEqual(self.row().own_key_last4, "9999")


class ModeTests(LLMSettingsTestCase):
    def test_own_key_mode_needs_a_stored_key(self):
        response = self.patch({"mode": "own_key"})
        self.assertEqual(
            (response.status_code, response.data["code"]), (400, "llm_key_required")
        )

    def test_toggle_keeps_the_key(self):
        self.save_key()
        self.assertEqual(
            self.patch({"mode": "own_key"}).data["data"]["mode"], "own_key"
        )
        self.assertEqual(
            self.patch({"mode": "resolve_ai"}).data["data"]["mode"], "resolve_ai"
        )
        self.assertTrue(self.row().has_key)

    def test_key_and_mode_can_be_set_together(self):
        response = self.patch(
            {"mode": "own_key", "own_provider": "gemini", "api_key": SECRET}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["mode"], "own_key")
        self.assertEqual(
            response.data["data"]["own_key"]["model"], "gemini-3.5-flash-lite"
        )

    def test_resolve_ai_model_must_be_a_cheap_one(self):
        ok = self.patch({"resolve_ai_model": "gemini-3.1-flash-lite"})
        self.assertEqual(ok.data["data"]["resolve_ai_model"], "gemini-3.1-flash-lite")
        for model in ("gemini-4-argon", "gpt-5-mini", "nope"):
            response = self.patch({"resolve_ai_model": model})
            self.assertEqual(
                (response.status_code, response.data["code"]),
                (400, "llm_model_not_allowed"),
            )
        self.assertEqual(self.row().resolve_ai_model, "gemini-3.1-flash-lite")

    def test_changing_the_model_rechecks_the_stored_key(self):
        self.save_key()
        self.create_provider.reset_mock()
        response = self.patch({"own_model": "gpt-4.1"})
        self.assertEqual(response.data["data"]["own_key"]["model"], "gpt-4.1")
        self.create_provider.assert_called_once_with("openai", SECRET, "gpt-4.1")
        self.assertEqual(self.row().own_key_last4, SECRET[-4:])

    def test_changing_provider_needs_a_new_key(self):
        self.save_key()
        response = self.patch({"own_provider": "gemini"})
        self.assertEqual(response.data["code"], "llm_key_required")
        self.assertEqual(self.row().own_provider, "openai")


class RemoveKeyTests(LLMSettingsTestCase):
    def test_removing_the_key_falls_back_to_resolve_ai(self):
        self.save_key()
        self.patch({"mode": "own_key"})
        response = self.member_client.delete(self.lurl("key/"))
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(
            (data["mode"], data["own_key"]["has_key"]), ("resolve_ai", False)
        )
        row = self.row()
        self.assertEqual(
            (row.own_key_encrypted, row.own_key_last4, row.own_provider), ("", "", "")
        )

    def test_removing_when_there_is_no_key_is_fine(self):
        response = self.member_client.delete(self.lurl("key/"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AuditEvent.objects.filter(action="llm.key_removed").exists())

    def test_non_members_get_404(self):
        self.assertEqual(
            self.stranger_client.delete(self.lurl("key/")).status_code, 404
        )


class CleanupTests(LLMSettingsTestCase):
    def test_leaving_the_workspace_deletes_the_key(self):
        self.save_key()
        self.member_client.post(f"/api/workspaces/{self.workspace_id}/leave/")
        self.assertFalse(UserWorkspaceLLMSettings.objects.exists())

    def test_being_removed_deletes_the_key_but_not_other_members(self):
        self.save_key()
        self.patch({"mode": "resolve_ai"}, self.owner_client)
        response = self.owner_client.delete(
            f"/api/workspaces/{self.workspace_id}/members/{self.member.id}/"
        )
        self.assertEqual(response.status_code, 200)
        users = list(UserWorkspaceLLMSettings.objects.values_list("user_id", flat=True))
        self.assertEqual(users, [self.owner.id])

    def test_deleting_the_account_row_cascades(self):
        self.save_key()
        self.member.delete()
        self.assertFalse(UserWorkspaceLLMSettings.objects.exists())


class AuditTests(LLMSettingsTestCase):
    def test_events_are_recorded_without_the_key(self):
        self.save_key()
        self.patch({"mode": "own_key"})
        self.member_client.delete(self.lurl("key/"))
        actions = list(
            AuditEvent.objects.filter(action__startswith="llm.")
            .order_by("created_at", "id")
            .values_list("action", flat=True)
        )
        self.assertEqual(
            actions,
            [
                "llm.key_saved",
                "llm.mode_changed",
                "llm.key_removed",
                "llm.mode_changed",
            ],
        )
        for event in AuditEvent.objects.filter(action__startswith="llm."):
            self.assertNotIn(SECRET, json.dumps(event.metadata))
            self.assertEqual(event.actor_user_id, self.member.id)
        saved = AuditEvent.objects.get(action="llm.key_saved")
        self.assertEqual(saved.metadata, {"provider": "openai", "model": "gpt-5-mini"})

    def test_unchanged_mode_records_nothing(self):
        self.patch({"mode": "resolve_ai"})
        self.assertFalse(AuditEvent.objects.filter(action="llm.mode_changed").exists())


class ProviderForTests(LLMSettingsTestCase):
    def test_default_is_resolve_ai_on_the_server_key(self):
        with mock.patch(
            "ai.services.settings_service.resolve_ai_provider",
            return_value=self.fake,
        ) as resolve:
            resolved = settings_service.provider_for(self.member, self.workspace_id)
        resolve.assert_called_once_with("gemini-3.5-flash-lite")
        self.assertTrue(resolved.uses_resolve_ai)

    def test_own_key_mode_uses_the_decrypted_key(self):
        self.save_key()
        self.patch({"mode": "own_key"})
        self.create_provider.reset_mock()
        resolved = settings_service.provider_for(self.member, self.workspace_id)
        self.assertFalse(resolved.uses_resolve_ai)
        self.create_provider.assert_called_once_with("openai", SECRET, "gpt-5-mini")

    def test_own_key_mode_ignored_when_the_key_was_removed(self):
        self.save_key()
        self.patch({"mode": "own_key"})
        self.member_client.delete(self.lurl("key/"))
        with mock.patch(
            "ai.services.settings_service.resolve_ai_provider",
            return_value=self.fake,
        ):
            self.assertTrue(
                settings_service.provider_for(
                    self.member, self.workspace_id
                ).uses_resolve_ai
            )

    def test_a_copied_row_does_not_open_for_another_user(self):
        self.save_key()
        stolen = self.row().own_key_encrypted
        with self.assertRaises(LLMInvalidKeyError):
            key_vault.unseal(self.workspace_id, self.owner.id, stolen)
        with self.assertRaises(LLMInvalidKeyError):
            key_vault.unseal(
                "00000000-0000-0000-0000-000000000000", self.member.id, stolen
            )
        with self.assertRaises(LLMInvalidKeyError):
            key_vault.unseal(self.workspace_id, self.member.id, "not-a-token")

    @override_settings(GEMINI_API_KEY="")
    def test_resolve_ai_without_a_server_key_is_unavailable(self):
        with self.assertRaises(LLMUnavailableError):
            settings_service.provider_for(self.member, self.workspace_id)
