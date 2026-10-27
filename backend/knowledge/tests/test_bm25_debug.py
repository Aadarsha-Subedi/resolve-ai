"""Temporary diagnostic (delete after use): prints BM25 data for the REFUND article."""

from unittest import skipUnless

from common.search.context import context_query
from knowledge.models import KnowledgeChunk
from knowledge.services import context_service
from knowledge.tests.test_bm25 import pg_search_available
from knowledge.tests.test_context import REFUND, ContextTestCase


@skipUnless(pg_search_available(), "needs ParadeDB")
class Bm25Debug(ContextTestCase):
    def test_print_scores(self):
        self.article("Refund policy", REFUND)
        self.article("Reset password", "Reset your password from the sign in page.")
        for text in (
            "How do I get a refund for my annual plan?",
            "annual plan refund 14 days",
        ):
            query = context_query(text, "english")
            print("\nQUERY", text, "-> terms", query.terms)
            for chunk_id, score in context_service._bm25_ranked(
                self.workspace_id, query
            ):
                chunk = KnowledgeChunk.objects.get(pk=chunk_id)
                print(f"  {score:.4f}  {chunk.heading_path!r}")
                print(f"           bm25_terms: {chunk.bm25_terms}")
