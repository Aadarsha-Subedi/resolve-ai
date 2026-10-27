from unittest import mock

from django.core.cache import cache
from django.test import override_settings

from common.rerank import RerankRateLimitedError
from common.rerank.fake import FakeReranker
from knowledge.services import context_service, rerank_service
from knowledge.tests.test_context import REFUND, ContextTestCase
from workspaces.models import Workspace


@override_settings(RERANK_DAILY_LIMIT=3)
class RerankTests(ContextTestCase):
    def setUp(self):
        super().setUp()
        self.article("Refund policy", REFUND)
        self.other = self.article("Refund tips", "A short note about refund timing.")

    def use(self, reranker):
        patcher = mock.patch.object(
            rerank_service, "get_reranker", return_value=reranker
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return reranker

    def retrieve(self, text="annual refund payment method"):
        workspace = Workspace.objects.get(pk=self.workspace_id)
        return context_service.retrieve_context(self.owner, workspace, text)

    def test_no_key_keeps_the_fused_order(self):
        self.use(None)
        result = self.retrieve()
        self.assertTrue(result.results)
        self.assertFalse(result.reranked)

    def test_reranker_orders_the_passages_and_sets_their_score(self):
        fake = self.use(FakeReranker())
        result = self.retrieve()
        self.assertTrue(result.reranked)
        scores = [p.score for p in result.results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(fake.calls[0]["top_n"], 5)
        self.assertIn("annual", result.results[0].text.lower())

    def test_only_this_workspaces_visible_text_is_sent(self):
        other = self.create_workspace(name="Other")["id"]
        self.article("Other refund", "SECRET other refund text", workspace_id=other)
        self.article("Draft refund", "SECRET draft refund text", publish=False)
        fake = self.use(FakeReranker())
        self.retrieve("refund")
        sent = " ".join(fake.calls[0]["documents"])
        self.assertNotIn("SECRET", sent)

    def test_provider_error_keeps_the_fused_order_and_is_not_counted(self):
        self.use(FakeReranker(error=RerankRateLimitedError()))
        result = self.retrieve()
        self.assertTrue(result.results)
        self.assertFalse(result.reranked)
        self.assertEqual(cache.get(rerank_service._usage_key(self.workspace_id)), 0)

    def test_daily_limit_keeps_the_fused_order(self):
        self.use(FakeReranker())
        self.assertTrue(all(self.retrieve().reranked for _ in range(3)))
        self.assertFalse(self.retrieve().reranked)

    def test_min_score_drops_weak_passages(self):
        self.use(FakeReranker())
        with mock.patch.object(context_service.cfg, "CONTEXT_RERANK_MIN_SCORE", 0.99):
            result = self.retrieve("annual refund payment method")
        self.assertTrue(result.reranked)
        self.assertTrue(all(p.score >= 0.99 for p in result.results))
