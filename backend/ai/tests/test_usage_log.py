from datetime import timedelta

from django.utils import timezone

from ai.constants import settings as cfg
from ai.models import AIUsageLog
from ai.services import usage_service
from workspaces.tests.base import WorkspaceTestCase


class UsageLogTests(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        self.workspace_id = self.workspace_with_member()

    def row(self, **extra):
        values = {
            "feature": cfg.USAGE_FEATURE_ASK,
            "outcome": cfg.USAGE_OUTCOME_LLM_CALL,
            "question": "How do refunds work?",
            "answer": "Within 14 days.",
            **extra,
        }
        usage_service.record(self.workspace_id, self.member.id, **values)

    def get(self, query="", client=None):
        return (client or self.owner_client).get(
            self.url(self.workspace_id, f"ai/usage/{query}")
        )

    def test_owner_sees_question_and_answer(self):
        self.row(input_tokens=10, output_tokens=5, details={"passages": []})
        response = self.get()
        self.assertEqual(response.status_code, 200, response.content)
        item = response.data["data"]["items"][0]
        self.assertEqual(item["question"], "How do refunds work?")
        self.assertEqual(item["answer"], "Within 14 days.")
        self.assertEqual(item["user"]["name"], "member")
        self.assertEqual(response.data["meta"]["summary"]["llm_calls"], 1)

    def test_member_and_stranger_cannot_read_it(self):
        self.row()
        self.assertEqual(self.get(client=self.member_client).status_code, 403)
        self.assertEqual(self.get(client=self.stranger_client).status_code, 404)

    def test_other_workspaces_rows_are_not_listed(self):
        other = self.create_workspace(name="Other")["id"]
        usage_service.record(
            other, self.owner.id, "ask", "llm_call", question="elsewhere"
        )
        self.row()
        items = self.get().data["data"]["items"]
        self.assertEqual([i["question"] for i in items], ["How do refunds work?"])

    def test_filters_search_and_summary(self):
        self.row()
        self.row(outcome=cfg.USAGE_OUTCOME_CACHE_HIT, question="refund policy?")
        self.row(feature=cfg.USAGE_FEATURE_REWRITE, question="shipping times")
        self.assertEqual(len(self.get("?search=shipping").data["data"]["items"]), 1)
        self.assertEqual(len(self.get("?search=member").data["data"]["items"]), 3)
        response = self.get("?feature=ask")
        self.assertEqual(len(response.data["data"]["items"]), 2)
        summary = response.data["meta"]["summary"]
        self.assertEqual((summary["cache_hits"], summary["llm_calls"]), (1, 1))
        self.assertEqual(summary["hit_rate"], 0.5)
        self.assertEqual(self.get("?outcome=cache_hit").data["meta"]["count"], 1)
        self.assertEqual(
            self.get("?actor=" + str(self.owner.id)).data["meta"]["count"], 0
        )

    def test_ordering_and_pagination(self):
        self.row(input_tokens=1)
        self.row(input_tokens=50, question="big")
        response = self.get("?ordering=-tokens&limit=1")
        self.assertEqual(response.data["data"]["items"][0]["question"], "big")
        self.assertEqual(response.data["meta"]["count"], 2)
        self.assertEqual(self.get("?ordering=bogus").status_code, 400)

    def test_old_rows_are_purged(self):
        self.row()
        AIUsageLog.objects.update(
            created_at=timezone.now() - timedelta(days=cfg.USAGE_RETENTION_DAYS + 1)
        )
        self.row(question="fresh")
        self.assertEqual(usage_service.purge_old(), 1)
        self.assertEqual(AIUsageLog.objects.get().question, "fresh")
