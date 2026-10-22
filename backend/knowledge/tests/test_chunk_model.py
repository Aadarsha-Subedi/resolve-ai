from unittest import skipUnless

from django.db import IntegrityError, connection, transaction

from knowledge.models import KnowledgeArticle, KnowledgeChunk
from knowledge.tests.base import KnowledgeTestCase

POSTGRES = connection.vendor == "postgresql"


class ChunkModelTests(KnowledgeTestCase):
    def setUp(self):
        super().setUp()
        self.article = KnowledgeArticle.objects.get(
            pk=self.create_article(title="Billing", content="")["id"]
        )

    def chunk(self, position, text="Refunds take five days.", **extra):
        return KnowledgeChunk.objects.create(
            workspace_id=self.workspace_id,
            article=self.article,
            position=position,
            heading_path="Billing > Refunds",
            text=text,
            **extra,
        )

    def test_positions_are_unique_within_an_article(self):
        self.chunk(0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.chunk(0)

    def test_chunks_are_removed_with_their_article(self):
        self.chunk(0)
        self.chunk(1)
        self.article.delete()
        self.assertEqual(KnowledgeChunk.objects.count(), 0)

    def test_chunks_are_removed_with_their_workspace_rows(self):
        self.chunk(0)
        KnowledgeArticle.objects.all().delete()
        self.assertEqual(KnowledgeChunk.objects.count(), 0)

    def test_defaults(self):
        chunk = self.chunk(0)
        self.assertEqual(chunk.search_language, "english")
        self.assertIsNone(chunk.search_vector)


@skipUnless(POSTGRES, "needs Postgres full-text search")
class ChunkPostgresTests(ChunkModelTests):
    def fill_vector(self):
        from django.contrib.postgres.search import SearchVector
        from django.db.models import F

        KnowledgeChunk.objects.update(
            search_vector=(
                SearchVector("heading_path", weight="A", config=F("search_language"))
                + SearchVector("text", weight="B", config=F("search_language"))
            )
        )

    def test_the_gin_index_exists(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexdef FROM pg_indexes WHERE tablename = 'knowledge_chunk'"
                " AND indexname = 'knowledge_chunk_search_gin'"
            )
            row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertIn("USING gin (search_vector)", row[0])

    def test_vector_filled_from_the_row_language_is_searchable(self):
        from common.search.query import search

        self.chunk(0, "Los reembolsos tardan cinco dias.", search_language="spanish")
        self.chunk(1, "Refunds take five days.")
        self.fill_vector()
        found = search(
            KnowledgeChunk.objects.all(),
            "reembolso",
            config="spanish",
            vector_field="search_vector",
        )
        self.assertEqual([c.position for c in found], [0])
        english = search(
            KnowledgeChunk.objects.all(),
            "refund",
            config="english",
            vector_field="search_vector",
        )
        self.assertEqual([c.position for c in english], [1])

    def test_heading_matches_rank_above_body_matches(self):
        from common.search.query import order_by_relevance, search

        self.chunk(0, "Nothing relevant here at all.")
        KnowledgeChunk.objects.filter(position=0).update(heading_path="Shipping times")
        self.chunk(1, "We ship every day and shipping takes two days.")
        self.fill_vector()
        ranked = order_by_relevance(
            search(
                KnowledgeChunk.objects.all(),
                "shipping",
                config="english",
                vector_field="search_vector",
            ),
            tiebreak=("position",),
        )
        self.assertEqual([c.position for c in ranked], [0, 1])
