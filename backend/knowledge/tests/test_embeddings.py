from io import StringIO
from unittest import mock, skipUnless

from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test import override_settings

from common.llm import LLMRateLimitedError
from common.llm.constants import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL
from common.llm.fake import FakeProvider
from knowledge.constants.settings import EMBED_RETRY_BACKOFF_SECONDS
from knowledge.models import KnowledgeChunk
from knowledge.services import embedding_service
from knowledge.tasks import embed_pending_chunks, embed_source
from knowledge.tests.base import KnowledgeTestCase
from knowledge.tests.test_upload_indexing import UploadIndexingTests

POSTGRES = connection.vendor == "postgresql"
TWO_SECTIONS = "# One\nFirst section text.\n\n# Two\nSecond section text."


@override_settings(GEMINI_API_KEY="server-key")
class EmbeddingTestCase(KnowledgeTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.provider = FakeProvider()
        patcher = mock.patch(
            "knowledge.services.embedding_service.resolve_ai_provider",
            return_value=self.provider,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def save_article(self, **extra):
        """Create an article and run the embedding task its commit queued."""
        with self.captureOnCommitCallbacks(execute=True):
            return self.create_article(title="Guide", content=TWO_SECTIONS, **extra)

    def chunks(self):
        return KnowledgeChunk.objects.order_by("position")


class ArticleEmbeddingTests(EmbeddingTestCase):
    def test_saving_an_article_embeds_its_chunks(self):
        self.save_article()
        chunks = list(self.chunks())
        self.assertEqual(len(chunks), 2)
        for chunk in chunks:
            self.assertEqual(len(chunk.embedding), EMBEDDING_DIMENSIONS)
            self.assertEqual(chunk.embedding_model, EMBEDDING_MODEL)
        texts, task = self.provider.embedded[0]
        self.assertEqual(task, "document")
        self.assertIn("Guide > One", texts[0])  # the heading path gives context
        self.assertIn("First section text.", texts[0])

    def test_nothing_is_queued_until_the_transaction_commits(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            self.create_article(title="Guide", content=TWO_SECTIONS)
        self.assertEqual(self.provider.embedded, [])
        self.assertTrue(callbacks)

    def test_an_edit_embeds_only_the_changed_passage(self):
        data = self.save_article()
        first = list(self.chunks())
        self.provider.embedded.clear()
        with self.captureOnCommitCallbacks(execute=True):
            self.owner_client.patch(
                self.kurl(f"articles/{data['id']}/"),
                {"content": "# One\nFirst section text.\n\n# Two\nSecond one changed."},
                format="json",
            )
        after = list(self.chunks())
        self.assertEqual(after[0].id, first[0].id)
        self.assertEqual(list(after[0].embedding), list(first[0].embedding))
        self.assertEqual(len(self.provider.embedded), 1)
        self.assertEqual(len(self.provider.embedded[0][0]), 1)  # one text, not two
        self.assertIsNotNone(after[1].embedding)

    def test_an_unchanged_save_queues_nothing(self):
        data = self.save_article()
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            self.owner_client.patch(
                self.kurl(f"articles/{data['id']}/"),
                {"content": TWO_SECTIONS},
                format="json",
            )
        self.assertEqual(callbacks, [])

    @override_settings(GEMINI_API_KEY="")
    def test_without_a_server_key_chunks_stay_unembedded(self):
        self.save_article()
        self.assertEqual(self.provider.embedded, [])
        self.assertTrue(all(c.embedding is None for c in self.chunks()))
        self.assertEqual(embedding_service.pending_sources(), [])

    def test_a_deleted_article_takes_its_vectors_with_it(self):
        data = self.save_article()
        self.owner_client.delete(self.kurl(f"articles/{data['id']}/"))
        self.assertFalse(KnowledgeChunk.objects.exists())


class UploadEmbeddingTests(EmbeddingTestCase):
    def test_indexing_an_upload_embeds_its_chunks(self):
        self.document_parser.markdown = (
            "# Setup\nInstall the agent.\n\n# Usage\nRun it daily."
        )
        UploadIndexingTests.make_upload(self)  # confirms, which queues indexing
        chunks = list(KnowledgeChunk.objects.filter(upload__isnull=False))
        self.assertTrue(chunks)
        self.assertTrue(all(c.embedding is not None for c in chunks))


class FailureTests(EmbeddingTestCase):
    def test_a_rate_limit_is_retried_and_keeps_finished_batches(self):
        self.save_article()
        KnowledgeChunk.objects.update(embedding=None, embedding_model="")
        self.provider.fail_with = LLMRateLimitedError()
        with (
            mock.patch.object(embed_source, "retry", side_effect=RuntimeError) as retry,
            self.assertRaises(RuntimeError),
        ):
            embed_source.push_request(retries=0)
            try:
                embed_source("article", str(KnowledgeChunk.objects.first().article_id))
            finally:
                embed_source.pop_request()
        self.assertEqual(
            retry.call_args.kwargs["countdown"], EMBED_RETRY_BACKOFF_SECONDS
        )
        self.assertTrue(all(c.embedding is None for c in self.chunks()))

    def test_after_the_last_retry_the_task_gives_up_quietly(self):
        self.save_article()
        KnowledgeChunk.objects.update(embedding=None, embedding_model="")
        self.provider.fail_with = LLMRateLimitedError()
        article_id = str(KnowledgeChunk.objects.first().article_id)
        embed_source.push_request(retries=embed_source.max_retries)
        try:
            self.assertEqual(embed_source("article", article_id), 0)
        finally:
            embed_source.pop_request()

    def test_the_sweeper_finishes_what_failed(self):
        self.save_article()
        KnowledgeChunk.objects.update(embedding=None, embedding_model="")
        self.assertEqual(embed_pending_chunks(), 1)
        self.assertTrue(all(c.embedding is not None for c in self.chunks()))
        self.assertEqual(embed_pending_chunks(), 0)

    def test_a_vector_from_an_older_model_is_recomputed(self):
        self.save_article()
        KnowledgeChunk.objects.update(embedding_model="old-model")
        self.assertEqual(embed_pending_chunks(), 1)
        self.assertEqual(
            set(KnowledgeChunk.objects.values_list("embedding_model", flat=True)),
            {EMBEDDING_MODEL},
        )


class DailyCapTests(EmbeddingTestCase):
    def test_chunks_over_the_cap_wait_for_the_next_day(self):
        with mock.patch.object(embedding_service, "EMBED_DAILY_CHUNK_LIMIT", 1):
            self.save_article()
            self.assertEqual(
                KnowledgeChunk.objects.filter(embedding__isnull=False).count(), 0
            )
            # The first batch (2 chunks) would pass the cap, so nothing is counted.
            self.assertEqual(self.provider.embedded, [])
        self.assertEqual(embed_pending_chunks(), 1)
        self.assertEqual(
            KnowledgeChunk.objects.filter(embedding__isnull=False).count(), 2
        )

    def test_usage_counts_embedded_chunks(self):
        self.save_article()
        workspace_id = KnowledgeChunk.objects.first().workspace_id
        self.assertEqual(cache.get(embedding_service._usage_key(workspace_id)), 2)

    def test_a_failed_batch_is_not_counted(self):
        self.save_article()
        KnowledgeChunk.objects.update(embedding=None, embedding_model="")
        workspace_id = KnowledgeChunk.objects.first().workspace_id
        before = cache.get(embedding_service._usage_key(workspace_id))
        self.provider.fail_with = LLMRateLimitedError()
        with self.assertRaises(LLMRateLimitedError):
            embedding_service.embed_source(
                "article", KnowledgeChunk.objects.first().article_id
            )
        self.assertEqual(cache.get(embedding_service._usage_key(workspace_id)), before)


class ReindexCommandTests(EmbeddingTestCase):
    def test_embeddings_flag_clears_vectors_for_the_sweep(self):
        self.save_article()
        out = StringIO()
        call_command("reindex_knowledge", "--embeddings", stdout=out)
        self.assertIn("cleared 2 embeddings", out.getvalue())
        self.assertEqual(
            KnowledgeChunk.objects.filter(embedding__isnull=False).count(), 0
        )
        embed_pending_chunks()
        self.assertEqual(
            KnowledgeChunk.objects.filter(embedding__isnull=False).count(), 2
        )


@skipUnless(POSTGRES, "needs pgvector")
class VectorIndexTests(EmbeddingTestCase):
    def test_nearest_chunk_by_cosine_distance(self):
        from pgvector.django import CosineDistance

        from common.llm.fake import fake_embedding

        self.save_article()
        nearest = (
            KnowledgeChunk.objects.annotate(
                distance=CosineDistance("embedding", fake_embedding("second section"))
            )
            .order_by("distance")
            .first()
        )
        self.assertEqual(nearest.heading_path, "Guide > Two")

    def test_hnsw_index_exists_and_is_used(self):
        from django.db import connection as conn

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT indexdef FROM pg_indexes WHERE indexname = %s",
                ["knowledge_chunk_embedding_hnsw"],
            )
            definition = cursor.fetchone()[0]
        self.assertIn("hnsw", definition)
        self.assertIn("vector_cosine_ops", definition)
