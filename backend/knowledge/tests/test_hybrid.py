import json
from unittest import mock, skipUnless

from django.test import override_settings

from common.documents import ParsedDocument, ParsedPage
from common.llm import LLMRateLimitedError, LLMResponse
from common.llm.fake import FakeProvider
from knowledge.models import KnowledgeChunk, KnowledgeUpload
from knowledge.services import answer_service, context_service, embedding_service
from knowledge.tasks import embed_pending_chunks
from knowledge.tests.test_context import (
    PASSWORD,
    POSTGRES,
    REFUND,
    ContextTestCase,
)
from knowledge.tests.test_upload_indexing import UploadIndexingTests

WARRANTY = ParsedDocument(
    pages=(
        ParsedPage(1, "# Warranty\n\nHardware repairs are covered for two years."),
        ParsedPage(
            2,
            "## Exclusions\n\nWater damage and accidental drops are not covered.",
        ),
    )
)


@skipUnless(POSTGRES, "needs Postgres and pgvector")
@override_settings(GEMINI_API_KEY="server-key")
class HybridTestCase(ContextTestCase):
    def setUp(self):
        super().setUp()
        self.provider = FakeProvider()
        for target, options in (
            (
                "knowledge.services.embedding_service.resolve_ai_provider",
                {"return_value": self.provider},
            ),
            (
                "knowledge.services.context_service.rewrite_query",
                {"return_value": []},
            ),
        ):
            patcher = mock.patch(target, **options)
            patcher.start()
            self.addCleanup(patcher.stop)

    def embed_all(self):
        embed_pending_chunks()
        self.provider.embedded.clear()

    def upload(self, parsed=WARRANTY):
        self.document_parser.parse = mock.Mock(return_value=parsed)
        upload = UploadIndexingTests.make_upload(self)
        self.embed_all()
        return upload

    def results(self, query):
        return self.ask(query).data["data"]["results"]


class VectorSearchTests(HybridTestCase):
    def test_vector_search_finds_what_the_word_search_misses(self):
        self.article("Refund policy", REFUND)
        self.article("Reset password", PASSWORD)
        self.embed_all()
        with mock.patch.object(context_service, "_ranked", return_value=[]):
            results = self.results("refund annual plan 14 days")
        self.assertEqual(results[0]["article"]["title"], "Refund policy")
        self.assertEqual(results[0]["source"]["type"], "article")

    def test_the_query_and_its_rewrites_are_embedded_in_one_request(self):
        self.article("Refund policy", REFUND)
        self.embed_all()
        with mock.patch(
            "knowledge.services.context_service.rewrite_query",
            return_value=["money back", "cancel plan"],
        ):
            self.results("refund annual plan")
        self.assertEqual(
            self.provider.embedded,
            [(["refund annual plan", "money back", "cancel plan"], "query")],
        )

    def test_unrelated_passages_are_below_the_similarity_bar(self):
        self.article("Reset password", PASSWORD)
        self.embed_all()
        with mock.patch.object(context_service, "_ranked", return_value=[]):
            self.assertEqual(self.results("zebra giraffe"), [])

    def test_chunks_from_another_embedding_model_are_ignored(self):
        self.article("Refund policy", REFUND)
        self.embed_all()
        KnowledgeChunk.objects.update(embedding_model="old-model")
        with mock.patch.object(context_service, "_ranked", return_value=[]):
            self.assertEqual(self.results("refund annual plan"), [])

    def test_a_passage_found_both_ways_is_not_listed_twice(self):
        self.article("Refund policy", REFUND)
        self.embed_all()
        results = self.results("refund annual plan")
        ids = [r["chunk_id"] for r in results]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(results[0]["section"], "Refund policy > Annual plans")

    def test_other_workspaces_are_never_searched(self):
        other = self.create_workspace(name="Other")["id"]
        self.article("Other refunds", REFUND, workspace_id=other)
        self.embed_all()
        with mock.patch.object(context_service, "_ranked", return_value=[]):
            self.assertEqual(self.results("refund annual plan"), [])


class FallbackTests(HybridTestCase):
    def test_if_embedding_fails_the_word_search_still_answers(self):
        self.article("Refund policy", REFUND)
        self.embed_all()
        self.provider.fail_with = LLMRateLimitedError()
        results = self.results("refund annual plan")
        self.assertEqual(results[0]["article"]["title"], "Refund policy")

    @override_settings(GEMINI_API_KEY="")
    def test_without_a_key_nothing_is_embedded_for_the_query(self):
        self.article("Refund policy", REFUND)
        self.assertTrue(self.results("refund annual plan"))
        self.assertEqual(self.provider.embedded, [])

    def test_the_daily_query_limit_turns_off_only_the_search_by_meaning(self):
        self.article("Refund policy", REFUND)
        self.embed_all()
        with mock.patch.object(embedding_service, "EMBED_QUERY_DAILY_LIMIT", 1):
            self.assertTrue(self.results("refund annual plan"))
            self.assertTrue(self.results("refund annual plan"))
        self.assertEqual(len(self.provider.embedded), 1)


class UploadSearchTests(HybridTestCase):
    def test_uploaded_documents_are_found_with_file_and_page(self):
        self.upload()
        results = self.results("water damage")
        self.assertEqual(len(results), 1)
        first = results[0]
        self.assertIsNone(first["article"])
        self.assertEqual(first["source"]["type"], "upload")
        self.assertEqual(first["source"]["title"], "Guide.pdf")
        self.assertEqual(first["source"]["page"], 2)
        self.assertEqual(first["section"], "Guide > Warranty > Exclusions")

    def test_articles_and_documents_are_ranked_together(self):
        self.article("Refund policy", REFUND)
        self.upload()
        kinds = {r["source"]["type"] for r in self.results("refund warranty repairs")}
        self.assertEqual(kinds, {"article", "upload"})

    def test_a_document_can_be_found_by_meaning_alone(self):
        self.upload()
        with mock.patch.object(context_service, "_ranked", return_value=[]):
            results = self.results("hardware repairs covered two years")
        self.assertEqual(results[0]["source"]["type"], "upload")

    def test_one_document_can_fill_every_slot(self):
        pages = tuple(
            ParsedPage(i, f"## Part {i}\n\nWarranty details {i}. " + "Warranty. " * 30)
            for i in range(1, 6)
        )
        self.upload(ParsedDocument(pages=pages))
        self.assertEqual(len(self.results("warranty")), 5)

    def test_a_document_that_is_not_ready_is_not_searched(self):
        upload = self.upload()
        KnowledgeUpload.objects.filter(pk=upload.pk).update(status="pending")
        self.assertEqual(self.results("water damage"), [])

    def test_a_deleted_document_is_gone_from_search(self):
        upload = self.upload()
        self.owner_client.delete(self.kurl(f"uploads/{upload.id}/"))
        self.assertEqual(self.results("water damage"), [])


class DocumentAnswerTests(HybridTestCase):
    def test_the_answer_cites_a_document_page(self):
        self.upload()
        with mock.patch.object(answer_service.llm_service, "generate") as generate:
            generate.return_value = LLMResponse(
                text=json.dumps({"answer": "Water damage is not covered [1]."}),
                model="fake",
            )
            response = self.member_client.post(
                self.kurl("ask/"), {"query": "water damage"}, format="json"
            )
        data = response.data["data"]
        self.assertTrue(data["answered"])
        self.assertEqual(data["cited"], [1])
        self.assertEqual(data["results"][0]["source"]["page"], 2)
        prompt = generate.call_args.args[2].prompt
        self.assertIn("Guide > Warranty > Exclusions (page 2)", prompt)
        self.assertIn("Water damage", prompt)

    def test_no_passages_means_no_llm_call(self):
        with mock.patch.object(answer_service.llm_service, "generate") as generate:
            response = self.member_client.post(
                self.kurl("ask/"), {"query": "zebra giraffe"}, format="json"
            )
        generate.assert_not_called()
        self.assertEqual(response.data["data"]["status"], "no_results")
        self.assertFalse(response.data["data"]["answered"])
