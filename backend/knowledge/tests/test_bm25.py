from unittest import mock, skipUnless

from django.db import DatabaseError, connection

from common.search.context import ContextQuery
from knowledge.models import KnowledgeChunk
from knowledge.services import context_service
from knowledge.tests.test_context import POSTGRES, REFUND, ContextTestCase


def pg_search_available() -> bool:
    if not POSTGRES:
        return False
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_search'")
        return cursor.fetchone() is not None


class Bm25FallbackTests(ContextTestCase):
    def test_database_error_falls_back_to_the_tsvector_search(self):
        query = ContextQuery(terms=["refund"], query=None)
        with mock.patch.object(context_service.connection, "cursor") as cursor:
            cursor.side_effect = DatabaseError("pg_search is missing")
            self.assertIsNone(context_service._bm25_ranked(self.workspace_id, query))


@skipUnless(POSTGRES, "needs Postgres")
class Bm25TermsTests(ContextTestCase):
    def test_terms_repeat_by_occurrence_and_heading_words_count_extra(self):
        self.article("Refund policy", REFUND)
        terms = KnowledgeChunk.objects.filter(
            workspace_id=self.workspace_id, bm25_terms__isnull=False
        ).values_list("bm25_terms", flat=True)
        self.assertTrue(terms)
        counts = [t.split().count("refund") for t in terms]
        # "refund" is in the title heading (counted twice) and in the body of one passage.
        self.assertTrue(all(c >= 2 for c in counts))
        self.assertGreater(max(counts), min(counts))


@skipUnless(
    pg_search_available(), "needs Postgres with the ParadeDB pg_search extension"
)
class Bm25RankingTests(ContextTestCase):
    def test_rare_word_outranks_common_word(self):
        self.article("Common", "refund refund refund refund refund")
        rare = self.article("Rare", "chargeback")
        for i in range(5):
            self.article(f"Filler {i}", "refund details")
        query = ContextQuery(terms=["refund", "chargeback"], query=None)
        ranked = context_service._bm25_ranked(self.workspace_id, query)
        articles = [
            str(KnowledgeChunk.objects.get(pk=chunk_id).article_id)
            for chunk_id, _ in ranked
        ]
        # BM25 statistics include rows other tests rolled back, so in a whole run the exact
        # first place is not stable; the rare word must still beat the plain "refund" filler.
        fillers = [a for a in articles if a != rare]
        self.assertIn(rare, articles[:2])
        self.assertLess(articles.index(rare), articles.index(fillers[-1]))

    def test_other_workspace_documents_are_never_returned(self):
        other = self.create_workspace(name="Other")["id"]
        self.article("Other refund", "refund elsewhere", workspace_id=other)
        query = ContextQuery(terms=["refund"], query=None)
        self.assertEqual(context_service._bm25_ranked(self.workspace_id, query), [])

    def test_drafts_are_not_returned(self):
        self.article("Draft refund", "refund draft", publish=False)
        query = ContextQuery(terms=["refund"], query=None)
        self.assertEqual(context_service._bm25_ranked(self.workspace_id, query), [])
