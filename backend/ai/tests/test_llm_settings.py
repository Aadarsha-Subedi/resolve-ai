import json
from unittest import mock

from cryptography.fernet import Fernet
from django.test import override_settings

from ai.models import UserWorkspaceLLMKey, UserWorkspaceLLMSettings
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

    def kurl(self, provider, workspace_id=None):
        return self.lurl(f"keys/{provider}/", workspace_id)

    def put(self, provider, body, client=None):
        return (client or self.member_client).put(
            self.kurl(provider), body, format="json"
        )

    def save_key(self, client=None, provider="openai", **extra):
        return self.put(provider, {"api_key": SECRET, **extra}, client)

    def delete_key(self, provider="openai", client=None):
        return (client or self.member_client).delete(self.kurl(provider))

    def row(self, user=None):
        return UserWorkspaceLLMSettings.objects.get(
            workspace_id=self.workspace_id, user=user or self.member
        )

    def key(self, provider="openai", user=None):
        return UserWorkspaceLLMKey.objects.get(
            workspace_id=self.workspace_id, user=user or self.member, provider=provider
        )


class ReadSettingsTests(LLMSettingsTestCase):
    def test_defaults_when_nothing_is_saved(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["mode"], "resolve_ai")
        self.assertEqual(data["resolve_ai_model"], "gemini-3.5-flash-lite")
        self.assertEqual((data["keys"], data["active_provider"]), ([], None))
        self.assertTrue(data["options"]["resolve_ai"]["available"])
        self.assertIn("gpt-5-mini", data["options"]["providers"]["openai"]["models"])
        self.assertFalse(UserWorkspaceLLMSettings.objects.exists())

    def test_non_members_get_404_and_anonymous_is_refused(self):
        self.assertEqual(self.get(self.stranger_client).status_code, 404)
        self.assertEqual(
            self.patch({"mode": "resolve_ai"}, self.stranger_client).status_code, 404
        )
        self.assertEqual(self.save_key(client=self.stranger_client).status_code, 404)
        from rest_framework.test import APIClient

        self.assertIn(APIClient().get(self.lurl()).status_code, (401, 403))

    def test_settings_are_private_to_each_user(self):
        self.save_key()
        self.assertEqual(self.get(self.owner_client).data["data"]["keys"], [])
        self.assertEqual(len(self.get().data["data"]["keys"]), 1)


class SaveKeyTests(LLMSettingsTestCase):
    def test_key_is_checked_encrypted_and_never_returned(self):
        response = self.save_key()
        self.assertEqual(response.status_code, 200)
        key = response.data["data"]["keys"][0]
        self.assertEqual(
            (key["provider"], key["model"], key["last4"]),
            ("openai", "gpt-5-mini", SECRET[-4:]),
        )
        self.assertNotIn(SECRET, json.dumps(response.data, default=str))
        self.assertNotIn(SECRET, json.dumps(self.get().data, default=str))
        self.create_provider.assert_called_with("openai", SECRET, "gpt-5-mini")
        row = self.key()
        self.assertNotIn(SECRET, row.key_encrypted)
        self.assertEqual(
            key_vault.unseal(self.workspace_id, self.member.id, row.key_encrypted),
            SECRET,
        )

    def test_the_first_key_becomes_active_and_switches_to_own_key_mode(self):
        data = self.save_key().data["data"]
        self.assertEqual((data["mode"], data["active_provider"]), ("own_key", "openai"))

    def test_a_second_key_does_not_change_the_active_one(self):
        self.save_key()
        data = self.save_key(provider="gemini").data["data"]
        self.assertEqual(data["active_provider"], "openai")
        self.assertEqual([k["provider"] for k in data["keys"]], ["openai", "gemini"])

    def test_rejected_key_is_not_saved(self):
        self.fake.key_valid = False
        response = self.save_key()
        self.assertEqual(
            (response.status_code, response.data["code"]), (400, "llm_invalid_key")
        )
        self.assertFalse(UserWorkspaceLLMKey.objects.exists())

    def test_provider_outage_is_a_503_and_nothing_is_saved(self):
        for error in (LLMTimeoutError(), LLMUnavailableError()):
            self.fake.validate_key = mock.Mock(side_effect=error)
            response = self.save_key()
            self.assertEqual(
                (response.status_code, response.data["code"]), (503, error.code)
            )
        self.assertFalse(UserWorkspaceLLMKey.objects.exists())

    def test_unknown_provider_is_404_and_unknown_model_is_refused(self):
        self.assertEqual(self.put("anthropic", {"api_key": SECRET}).status_code, 404)
        self.assertEqual(self.delete_key("anthropic").status_code, 404)
        response = self.save_key(model="gpt-99")
        self.assertEqual(
            (response.status_code, response.data["code"]),
            (400, "llm_model_not_allowed"),
        )
        response = self.save_key(provider="gemini", model="gpt-5-mini")
        self.assertEqual(response.data["code"], "llm_model_not_allowed")
        self.assertFalse(UserWorkspaceLLMKey.objects.exists())

    def test_a_new_key_needs_the_key_itself(self):
        response = self.put("openai", {"model": "gpt-4.1"})
        self.assertEqual(
            (response.status_code, response.data["code"]), (400, "llm_key_required")
        )

    def test_bad_bodies_are_rejected(self):
        self.assertEqual(self.put("openai", {}).status_code, 400)
        self.assertEqual(self.put("openai", {"api_key": "short"}).status_code, 400)
        self.assertEqual(
            self.put("openai", {"api_key": "has a space inside"}).status_code, 400
        )
        self.assertEqual(self.put("openai", {"surprise": 1}).status_code, 400)
        self.assertEqual(self.patch({}).status_code, 400)
        self.assertEqual(self.patch({"mode": "other"}).status_code, 400)
        self.assertEqual(self.patch({"active_provider": "anthropic"}).status_code, 400)

    def test_replacing_a_key_updates_last4_and_keeps_the_model(self):
        self.save_key(model="gpt-4.1")
        self.put("openai", {"api_key": "sk-another-key-9999"})
        key = self.key()
        self.assertEqual((key.key_last4, key.model), ("9999", "gpt-4.1"))

    def test_changing_only_the_model_rechecks_the_stored_key(self):
        self.save_key()
        self.create_provider.reset_mock()
        response = self.put("openai", {"model": "gpt-4.1"})
        self.assertEqual(response.data["data"]["keys"][0]["model"], "gpt-4.1")
        self.create_provider.assert_called_once_with("openai", SECRET, "gpt-4.1")
        self.assertEqual(self.key().key_last4, SECRET[-4:])


class ModeTests(LLMSettingsTestCase):
    def test_own_key_mode_needs_a_stored_key(self):
        response = self.patch({"mode": "own_key"})
        self.assertEqual(
            (response.status_code, response.data["code"]), (400, "llm_key_required")
        )

    def test_toggle_keeps_the_keys(self):
        self.save_key()
        self.assertEqual(
            self.patch({"mode": "resolve_ai"}).data["data"]["mode"], "resolve_ai"
        )
        self.assertEqual(
            self.patch({"mode": "own_key"}).data["data"]["mode"], "own_key"
        )
        self.assertTrue(UserWorkspaceLLMKey.objects.exists())

    def test_the_active_provider_can_be_switched_between_saved_keys(self):
        self.save_key()
        self.save_key(provider="gemini")
        data = self.patch({"active_provider": "gemini"}).data["data"]
        self.assertEqual(data["active_provider"], "gemini")
        response = self.patch({"active_provider": "openai"}, self.owner_client)
        self.assertEqual(response.data["code"], "llm_key_required")

    def test_active_provider_needs_a_saved_key(self):
        self.save_key()
        response = self.patch({"active_provider": "gemini"})
        self.assertEqual(
            (response.status_code, response.data["code"]), (400, "llm_key_required")
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


class RemoveKeyTests(LLMSettingsTestCase):
    def test_removing_the_only_key_falls_back_to_resolve_ai(self):
        self.save_key()
        response = self.delete_key()
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(
            (data["mode"], data["keys"], data["active_provider"]),
            ("resolve_ai", [], None),
        )
        self.assertFalse(UserWorkspaceLLMKey.objects.exists())

    def test_removing_the_active_key_hands_over_to_the_next(self):
        self.save_key()
        self.save_key(provider="gemini")
        data = self.delete_key("openai").data["data"]
        self.assertEqual((data["mode"], data["active_provider"]), ("own_key", "gemini"))

    def test_removing_an_inactive_key_changes_nothing_else(self):
        self.save_key()
        self.save_key(provider="gemini")
        data = self.delete_key("gemini").data["data"]
        self.assertEqual((data["mode"], data["active_provider"]), ("own_key", "openai"))

    def test_removing_when_there_is_no_key_is_fine(self):
        response = self.delete_key()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AuditEvent.objects.filter(action="llm.key_removed").exists())

    def test_non_members_get_404(self):
        self.assertEqual(self.delete_key(client=self.stranger_client).status_code, 404)


class CleanupTests(LLMSettingsTestCase):
    def test_leaving_the_workspace_deletes_the_keys(self):
        self.save_key()
        self.member_client.post(f"/api/workspaces/{self.workspace_id}/leave/")
        self.assertFalse(UserWorkspaceLLMKey.objects.exists())
        self.assertFalse(UserWorkspaceLLMSettings.objects.exists())

    def test_being_removed_deletes_the_keys_but_not_other_members(self):
        self.save_key()
        self.save_key(client=self.owner_client)
        response = self.owner_client.delete(
            f"/api/workspaces/{self.workspace_id}/members/{self.member.id}/"
        )
        self.assertEqual(response.status_code, 200)
        users = list(UserWorkspaceLLMKey.objects.values_list("user_id", flat=True))
        self.assertEqual(users, [self.owner.id])

    def test_deleting_the_account_row_cascades(self):
        self.save_key()
        self.member.delete()
        self.assertFalse(UserWorkspaceLLMKey.objects.exists())
        self.assertFalse(UserWorkspaceLLMSettings.objects.exists())


class AuditTests(LLMSettingsTestCase):
    def test_events_are_recorded_without_the_key(self):
        self.save_key()
        self.delete_key()
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

    def test_a_model_only_edit_is_not_a_key_save(self):
        self.save_key()
        self.put("openai", {"model": "gpt-4.1"})
        self.assertEqual(AuditEvent.objects.filter(action="llm.key_saved").count(), 1)

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

    def test_own_key_mode_uses_the_active_providers_decrypted_key(self):
        self.save_key()
        self.save_key(provider="gemini")
        self.patch({"active_provider": "gemini"})
        self.create_provider.reset_mock()
        resolved = settings_service.provider_for(self.member, self.workspace_id)
        self.assertFalse(resolved.uses_resolve_ai)
        self.create_provider.assert_called_once_with(
            "gemini", SECRET, "gemini-3.5-flash-lite"
        )

    def test_resolve_ai_mode_ignores_saved_keys(self):
        self.save_key()
        self.patch({"mode": "resolve_ai"})
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
        stolen = self.key().key_encrypted
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
