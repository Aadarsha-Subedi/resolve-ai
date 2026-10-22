from unittest import mock, skipUnless

from django.core.cache import cache
from django.db import connection
from django.test import override_settings

from knowledge.models import KnowledgeChunk
from knowledge.services import context_service
from knowledge.tests.base import KnowledgeTestCase

POSTGRES = connection.vendor == "postgresql"

REFUND = (
    "# Refund policy\n\n"
    "## Annual plans\n"
    "You can request a refund within 14 days of purchase for an annual plan. "
    "The refund goes back to the original payment method.\n\n"
    "## Monthly plans\n"
    "Monthly plans are not refunded after they renew."
)
PASSWORD = (
    "# Reset password\n\nOpen the sign in page and choose Forgot password. "
    "We email you a link to choose a new password."
)


@override_settings(GEMINI_API_KEY="", LLM_CALL_LIMIT=100)
class ContextTestCase(KnowledgeTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def publish(self, article_id, workspace_id=None, client=None):
        response = (client or self.owner_client).post(
            self.kurl(f"articles/{article_id}/publish/", workspace_id)
        )
        assert response.status_code == 200, response.content

    def article(self, title, content, publish=True, workspace_id=None):
        ws = workspace_id or self.workspace_id
        response = self.owner_client.post(
            self.kurl("articles/", ws),
            {"title": title, "content": content},
            format="json",
        )
        assert response.status_code == 201, response.content
        article_id = response.data["data"]["id"]
        if publish:
            self.publish(article_id, ws)
        return article_id

    def ask(self, query, client=None, workspace_id=None):
        return (client or self.member_client).post(
            self.kurl("context/", workspace_id), {"query": query}, format="json"
        )

    def titles(self, response):
        return [r["article"]["title"] for r in response.data["data"]["results"]]


class IsolationTests(ContextTestCase):
    def test_only_published_articles_of_this_workspace(self):
        self.article("Refund policy", REFUND)
        draft = self.article("Draft refunds", "Refund draft text", publish=False)
        archived = self.article("Old refunds", "Refund archived text")
        self.owner_client.post(self.kurl(f"articles/{archived}/archive/"))
        other = self.create_workspace(name="Other")["id"]
        self.article("Other refund", "Refund elsewhere", workspace_id=other)
        response = self.ask("refund")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(self.titles(response)), {"Refund policy"})
        self.assertTrue(draft)

    def test_unpublishing_hides_the_article_at_once(self):
        article_id = self.article("Refund policy", REFUND)
        self.assertEqual(self.titles(self.ask("refund")), ["Refund policy"] * 2)
        self.owner_client.post(self.kurl(f"articles/{article_id}/unpublish/"))
        self.assertEqual(self.titles(self.ask("refund")), [])

    def test_non_members_get_404_and_anonymous_is_refused(self):
        self.article("Refund policy", REFUND)
        self.assertEqual(self.ask("refund", self.stranger_client).status_code, 404)
        from rest_framework.test import APIClient

        response = APIClient().post(
            self.kurl("context/"), {"query": "refund"}, format="json"
        )
        self.assertIn(response.status_code, (401, 403))

    def test_text_without_usable_words_returns_nothing_not_an_error(self):
        self.article("Refund policy", REFUND)
        response = self.ask("the and of")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["results"], [])
        self.assertEqual(response.data["data"]["terms"], [])


class ValidationTests(ContextTestCase):
    def test_bad_bodies(self):
        for body in (
            {},
            {"query": "a"},
            {"query": "x" * 2001},
            {"query": "ok", "z": 1},
        ):
            response = self.member_client.post(
                self.kurl("context/"), body, format="json"
            )
            self.assertEqual(response.status_code, 400, body)

    def test_thirty_first_call_in_a_minute_is_throttled(self):
        statuses = [self.ask("refund").status_code for _ in range(31)]
        self.assertEqual(statuses[:30], [200] * 30)
        self.assertEqual(statuses[30], 429)


@skipUnless(POSTGRES, "needs Postgres full-text search")
class RankingTests(ContextTestCase):
    def test_results_have_citations_scores_sections_and_snippets(self):
        self.article("Refund policy", REFUND)
        self.article("Reset password", PASSWORD)
        data = self.ask("How do I get a refund for my annual plan?").data["data"]
        first = data["results"][0]
        self.assertEqual(first["citation"], 1)
        self.assertEqual(first["article"]["title"], "Refund policy")
        self.assertEqual(first["section"], "Refund policy > Annual plans")
        self.assertIn("⟦", first["snippet"])
        self.assertTrue(0 < first["score"] <= 1)
        self.assertEqual(
            [r["citation"] for r in data["results"]],
            list(range(1, len(data["results"]) + 1)),
        )
        self.assertNotIn(
            "Reset password", [r["article"]["title"] for r in data["results"]]
        )
        self.assertFalse(data["rewritten"])
        self.assertIn("refund", data["terms"])

    def test_the_best_matching_section_comes_first(self):
        self.article("Refund policy", REFUND)
        results = self.ask("annual plan refund 14 days").data["data"]["results"]
        self.assertEqual(results[0]["section"], "Refund policy > Annual plans")

    def test_at_most_two_passages_per_article(self):
        sections = "\n\n".join(
            f"## Part {i}\nRefund details number {i}. " + "Refund words. " * 40
            for i in range(5)
        )
        self.article("Refund handbook", "# Refund handbook\n\n" + sections)
        results = self.ask("refund").data["data"]["results"]
        self.assertEqual(len(results), 2)

    def test_at_most_five_passages_overall(self):
        for i in range(8):
            self.article(f"Refund note {i}", f"Refund note number {i} about refunds.")
        self.assertEqual(len(self.ask("refund").data["data"]["results"]), 5)

    def test_weak_matches_are_dropped(self):
        self.article("Reset password", PASSWORD)
        self.assertEqual(self.ask("zebra giraffe").data["data"]["results"], [])

    def test_one_stray_body_word_does_not_count_when_there_are_many_words(self):
        self.article("Refund policy", REFUND)
        # "back" is in the body of the annual plans section and nothing else matches.
        self.assertEqual(self.ask("I want my money back").data["data"]["results"], [])
        # On its own, the same word is an acceptable (if weak) match.
        self.assertEqual(len(self.ask("back").data["data"]["results"]), 1)

    def test_the_search_can_use_the_gin_index(self):
        from common.search.context import context_query
        from common.search.query import search_with_query

        self.article("Refund policy", REFUND)
        query = context_query("annual plan refund", "english").query
        # Not filtered by workspace here: on a table this small the planner would
        # otherwise pick the (workspace, article, position) index instead.
        queryset = search_with_query(
            KnowledgeChunk.objects.all(),
            query,
            vector_field="search_vector",
        )
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL enable_seqscan = off")
            cursor.execute(
                "SET LOCAL enable_indexscan = off"
            )  # leaves the bitmap GIN scan
            plan = queryset.explain()
        self.assertIn("knowledge_chunk_search_gin", plan)

    def test_a_chunk_matching_several_wordings_rises(self):
        a = [("c1", 0.9), ("c2", 0.8)]
        b = [("c2", 0.7), ("c3", 0.6)]
        merged = context_service._merge([a, b])
        self.assertEqual([c for c, _ in merged], ["c2", "c1", "c3"])
        self.assertEqual(dict(merged)["c2"], 0.8)  # best raw score is kept


@skipUnless(POSTGRES, "needs Postgres full-text search")
class RewriteTests(ContextTestCase):
    def setUp(self):
        super().setUp()
        self.article("Refund policy", REFUND)
        patcher = mock.patch(
            "knowledge.services.context_service.rewrite_query",
            return_value=["refund annual plan", "cancel subscription"],
        )
        self.rewrite = patcher.start()
        self.addCleanup(patcher.stop)

    def test_rewrites_find_what_the_original_words_miss(self):
        data = self.ask("I want my money back").data["data"]
        self.assertTrue(data["rewritten"])
        self.assertEqual(data["queries"], ["refund annual plan", "cancel subscription"])
        self.assertEqual(
            self.titles(self.ask("I want my money back"))[0], "Refund policy"
        )

    def test_without_rewrites_the_original_is_searched_alone(self):
        self.rewrite.return_value = []
        data = self.ask("I want my money back").data["data"]
        self.assertFalse(data["rewritten"])
        self.assertEqual(data["results"], [])

    def test_the_same_text_is_rewritten_once(self):
        self.ask("I want my money back")
        self.ask("I want my money back")
        self.assertEqual(self.rewrite.call_count, 1)

    def test_failed_rewrites_are_not_remembered(self):
        self.rewrite.return_value = []
        self.ask("I want my money back")
        self.ask("I want my money back")
        self.assertEqual(self.rewrite.call_count, 2)


class SyncTests(ContextTestCase):
    def test_passages_follow_article_edits(self):
        article_id = self.article("Refund policy", REFUND)
        self.assertTrue(KnowledgeChunk.objects.filter(article_id=article_id).exists())
        self.owner_client.patch(
            self.kurl(f"articles/{article_id}/"),
            {"content": "# Refund policy\n\nWe no longer discuss it."},
            format="json",
        )
        if POSTGRES:
            self.assertEqual(self.ask("annual plan").data["data"]["results"], [])
