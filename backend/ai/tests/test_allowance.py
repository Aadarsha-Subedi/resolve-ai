from datetime import date
from unittest import mock

from django.core.cache import cache
from django.test import override_settings

from ai.services import allowance, llm_service
from ai.services.allowance import LLMAllowanceExhaustedError
from ai.tests.test_llm_settings import LLMSettingsTestCase
from common.llm import LLMRequest

REQUEST = LLMRequest(prompt="hello")


@override_settings(LLM_CALL_LIMIT=3)
class AllowanceTests(LLMSettingsTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        patcher = mock.patch(
            "ai.services.settings_service.resolve_ai_provider", return_value=self.fake
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def call(self, user=None, workspace_id=None):
        return llm_service.generate(
            user or self.member, workspace_id or self.workspace_id, REQUEST
        )

    def test_calls_are_counted_until_the_limit_then_refused(self):
        for _ in range(3):
            self.call()
        with self.assertRaises(LLMAllowanceExhaustedError) as raised:
            self.call()
        self.assertEqual(raised.exception.code, "llm_allowance_exhausted")
        self.assertEqual(
            len(self.fake.requests), 3
        )  # the 4th never reached the provider
        usage = allowance.usage(self.workspace_id, self.member.id)
        self.assertEqual((usage.limit, usage.remaining), (3, 0))

    def test_each_user_and_workspace_has_its_own_allowance(self):
        for _ in range(3):
            self.call()
        self.call(user=self.owner)  # another user, same workspace
        other = self.create_workspace(self.member_client, name="Other")["id"]
        self.call(workspace_id=other)  # same user, another workspace

    def test_the_count_starts_again_the_next_day(self):
        for _ in range(3):
            self.call()
        with mock.patch.object(allowance, "_today", return_value=date(2999, 1, 1)):
            self.call()
            self.assertEqual(allowance.usage(self.workspace_id, self.member.id).used, 1)

    def test_own_key_calls_are_not_counted(self):
        self.save_key()
        self.patch({"mode": "own_key"})
        for _ in range(5):
            self.call()
        self.assertEqual(allowance.usage(self.workspace_id, self.member.id).used, 0)
        self.assertEqual(len(self.fake.requests), 5)

    def test_settings_response_shows_usage(self):
        self.call()
        usage = self.get().data["data"]["usage"]
        self.assertEqual(
            (usage["used_today"], usage["limit"], usage["remaining"]), (1, 3, 2)
        )
        self.assertTrue(usage["resets_at"].endswith("+00:00"))
