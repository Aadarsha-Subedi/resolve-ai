from unittest import skipUnless

from django.db import IntegrityError, connection, transaction

from knowledge.models import KnowledgeArticle, KnowledgeChunk, KnowledgeUpload
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


class UploadChunkModelTests(KnowledgeTestCase):
    def setUp(self):
        super().setUp()
        self.upload = KnowledgeUpload.objects.create(
            workspace_id=self.workspace_id,
            filename="Guide.pdf",
            content_type="application/pdf",
            size_bytes=10,
            storage_key="workspaces/x/knowledge/uploads/guide.pdf",
            status="ready",
        )
        self.article = KnowledgeArticle.objects.get(
            pk=self.create_article(title="Billing", content="")["id"]
        )

    def chunk(self, position, **extra):
        values = {
            "workspace_id": self.workspace_id,
            "position": position,
            "heading_path": "Guide > Refunds",
            "text": "Refunds take five days.",
            **extra,
        }
        return KnowledgeChunk.objects.create(**values)

    def test_an_upload_chunk_records_its_page(self):
        chunk = self.chunk(0, upload=self.upload, page=3)
        chunk.refresh_from_db()
        self.assertEqual(
            (chunk.upload_id, chunk.article_id, chunk.page), (self.upload.id, None, 3)
        )

    def test_exactly_one_source_is_required(self):
        for sources in ({}, {"article": self.article, "upload": self.upload}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                self.chunk(0, **sources)

    def test_positions_are_unique_within_an_upload_but_not_across_sources(self):
        self.chunk(0, upload=self.upload)
        self.chunk(0, article=self.article)  # same position, other source
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.chunk(0, upload=self.upload)

    def test_chunks_are_removed_with_their_upload(self):
        self.chunk(0, upload=self.upload)
        self.chunk(1, upload=self.upload)
        self.chunk(0, article=self.article)
        self.upload.delete()
        self.assertEqual(
            list(KnowledgeChunk.objects.values_list("article_id", flat=True)),
            [self.article.id],
        )

    def test_article_search_ignores_upload_chunks(self):
        from knowledge.constants.enums import ArticleStatus

        KnowledgeArticle.objects.filter(pk=self.article.pk).update(
            status=ArticleStatus.PUBLISHED
        )
        self.chunk(0, upload=self.upload)
        published = KnowledgeChunk.objects.filter(
            article__status=ArticleStatus.PUBLISHED
        )
        self.assertEqual(published.count(), 0)


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

    def test_the_source_constraints_and_indexes_exist(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT conname FROM pg_constraint WHERE conrelid = 'knowledge_chunk'::regclass"
            )
            constraints = {row[0] for row in cursor.fetchall()}
            cursor.execute(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'knowledge_chunk'"
            )
            indexes = {row[0] for row in cursor.fetchall()}
        self.assertTrue(
            {
                "chunk_has_exactly_one_source",
                "unique_chunk_position",
                "unique_upload_chunk_position",
            }
            <= constraints
        )
        self.assertTrue(
            {"knowledge_chunk_ws_upl_pos", "knowledge_chunk_search_gin"} <= indexes
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
