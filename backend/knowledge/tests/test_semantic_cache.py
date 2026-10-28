from unittest import mock, skipUnless

from django.db import connection

from ai.models import AIUsageLog
from ai.services.settings_service import ResolvedProvider
from common.llm.fake import FakeProvider
from knowledge.models import AskCacheEntry
from knowledge.services import answer_service, cache_service
from knowledge.services.answer_service import ANSWERED, AnswerResult
from knowledge.services.cache_service import Lookup
from knowledge.services.context_service import ContextResult, Passage
from knowledge.tests.base import KnowledgeTestCase

POSTGRES = connection.vendor == "postgresql"
PASSAGE = Passage("c1", "article", "a1", "Refund policy", "Refunds", "x", 1.0, "text")
CACHED = {
    "cached": False,
    "terms": [],
    "queries": [],
    "rewritten": False,
    "results": [
        {
            "citation": 1,
            "score": 1.0,
            "article": {"id": "a1", "title": "Refund policy"},
            "source": {
                "type": "article",
                "id": "a1",
                "title": "Refund policy",
                "page": None,
            },
            "section": "Refunds",
            "chunk_id": "c1",
            "snippet": "x",
        }
    ],
    "answered": True,
    "status": "answered",
    "reason": None,
    "answer": "Refunds take 14 days. [1]",
    "cited": [1],
    "claims": [],
}


class SemanticCacheFlowTests(KnowledgeTestCase):
    """The ask flow around the cache; the lookup itself is mocked so SQLite can run this."""

    def setUp(self):
        super().setUp()
        provider = FakeProvider()
        for target, options in (
            (
                "knowledge.services.answer_service.settings_service.provider_for",
                {"return_value": ResolvedProvider(provider, True)},
            ),
            ("knowledge.services.answer_service.cache_service.store", {}),
        ):
            patcher = mock.patch(target, **options)
            mocked = patcher.start()
            self.addCleanup(patcher.stop)
            if target.endswith(".store"):
                self.store = mocked
        patcher = mock.patch("knowledge.services.answer_service.cache_service.lookup")
        self.lookup = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(answer_service, "_answer")
        self.answer = patcher.start()
        self.addCleanup(patcher.stop)

    def ask(self, query="how long do refunds take?"):
        return self.member_client.post(
            self.kurl("ask/"), {"query": query}, format="json"
        )

    def test_a_hit_replays_the_cached_answer_without_searching_or_calling_the_llm(self):
        self.lookup.return_value = Lookup(
            [0.0], "gemini:fake-model", CACHED, 0.95, "how long for a refund?"
        )
        data = self.ask().data["data"]
        self.answer.assert_not_called()
        self.assertTrue(data["cached"])
        self.assertEqual(data["answer"], "Refunds take 14 days. [1]")
        row = AIUsageLog.objects.get()
        self.assertEqual((row.feature, row.outcome), ("ask", "cache_hit"))
        self.assertEqual(row.answer, "Refunds take 14 days. [1]")
        self.assertEqual(row.details["similarity"], 0.95)
        self.assertEqual(row.details["passages"][0]["title"], "Refund policy")

    def test_a_miss_answers_stores_and_logs_the_llm_call(self):
        found = Lookup([0.0], "gemini:fake-model")
        self.lookup.return_value = found
        self.answer.return_value = AnswerResult(
            ContextResult([PASSAGE]),
            ANSWERED,
            answer="Refunds take 14 days. [1]",
            cited=[1],
            usage={"model": "fake-model", "input_tokens": 7, "output_tokens": 3},
        )
        data = self.ask().data["data"]
        self.assertFalse(data["cached"])
        self.store.assert_called_once()
        self.assertIs(self.store.call_args.args[2], found)
        row = AIUsageLog.objects.get()
        self.assertEqual(
            (row.outcome, row.input_tokens, row.output_tokens), ("llm_call", 7, 3)
        )

    def test_unanswered_questions_are_not_cached(self):
        self.lookup.return_value = Lookup([0.0], "gemini:fake-model")
        self.answer.return_value = AnswerResult(
            ContextResult([PASSAGE]), "not_covered", usage={"model": "m"}
        )
        self.ask()
        self.store.assert_not_called()

    def test_no_embedding_means_no_cache_and_a_normal_answer(self):
        self.lookup.return_value = None
        self.answer.return_value = AnswerResult(ContextResult(), "no_results")
        self.assertEqual(self.ask().status_code, 200)
        self.store.assert_not_called()
        self.assertEqual(AIUsageLog.objects.count(), 0)

    def test_a_failed_llm_call_is_logged_as_an_error(self):
        self.lookup.return_value = None
        self.answer.return_value = AnswerResult(
            ContextResult([PASSAGE]), "unavailable", usage={"error_code": "llm_timeout"}
        )
        self.ask()
        row = AIUsageLog.objects.get()
        self.assertEqual((row.outcome, row.error_code), ("error", "llm_timeout"))


class CacheClearingTests(KnowledgeTestCase):
    def entry(self, workspace_id=None):
        return AskCacheEntry.objects.create(
            workspace_id=workspace_id or self.workspace_id,
            question="q",
            embedding=[0.0] * 768,
            embedding_model="m",
            llm_model="gemini:x",
            payload={},
        )

    @skipUnless(POSTGRES, "needs pgvector")
    def test_editing_publishing_or_deleting_knowledge_clears_the_workspace_cache(self):
        other = self.create_workspace(name="Other")["id"]
        self.entry(other)
        article = self.create_article()
        for action in (
            lambda: self.owner_client.patch(
                self.kurl(f"articles/{article['id']}/"), {"title": "New"}, format="json"
            ),
            lambda: self.owner_client.post(
                self.kurl(f"articles/{article['id']}/publish/")
            ),
            lambda: self.owner_client.delete(self.kurl(f"articles/{article['id']}/")),
        ):
            self.entry()
            with self.captureOnCommitCallbacks(execute=True):
                action()
            self.assertEqual(
                AskCacheEntry.objects.filter(workspace_id=self.workspace_id).count(), 0
            )
        self.assertEqual(AskCacheEntry.objects.filter(workspace_id=other).count(), 1)


@skipUnless(POSTGRES, "needs pgvector")
class CacheLookupTests(KnowledgeTestCase):
    def setUp(self):
        super().setUp()
        self.provider = FakeProvider()
        patcher = mock.patch(
            "knowledge.services.embedding_service.resolve_ai_provider",
            return_value=self.provider,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch(
            "knowledge.services.embedding_service.is_configured", return_value=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_similar_question_hits_and_an_unrelated_one_misses(self):
        miss = cache_service.lookup(
            self.member.id, self.workspace_id, "refund annual plan days", "gemini:x"
        )
        self.assertIsNone(miss.payload)
        cache_service.store(
            self.workspace_id, "refund annual plan days", miss, {"a": 1}
        )
        hit = cache_service.lookup(
            self.member.id, self.workspace_id, "refund annual plan days", "gemini:x"
        )
        self.assertEqual(hit.payload, {"a": 1})
        self.assertGreaterEqual(hit.similarity, 0.99)
        other = cache_service.lookup(
            self.member.id, self.workspace_id, "reset my password", "gemini:x"
        )
        self.assertIsNone(other.payload)

    def test_another_model_or_workspace_never_hits(self):
        found = cache_service.lookup(
            self.member.id, self.workspace_id, "refund annual plan days", "gemini:x"
        )
        cache_service.store(
            self.workspace_id, "refund annual plan days", found, {"a": 1}
        )
        self.assertIsNone(
            cache_service.lookup(
                self.member.id, self.workspace_id, "refund annual plan days", "openai:y"
            ).payload
        )
        other = self.create_workspace(name="Other")["id"]
        self.assertIsNone(
            cache_service.lookup(
                self.owner.id, other, "refund annual plan days", "gemini:x"
            ).payload
        )
