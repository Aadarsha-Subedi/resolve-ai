from datetime import timedelta
from io import StringIO
from unittest import mock

from celery.exceptions import Retry
from django.core.management import call_command
from django.utils import timezone

from common.documents import (
    DocumentCorruptError,
    DocumentEmptyError,
    ParsedDocument,
    ParsedPage,
)
from knowledge import tasks
from knowledge.constants.enums import IndexStatus
from knowledge.models import KnowledgeUpload
from knowledge.services import upload_index_service, upload_service
from knowledge.tests.base import KnowledgeTestCase

PDF = b"%PDF-1.4\n" + b"x" * 100


class UploadIndexingTests(KnowledgeTestCase):
    def make_upload(self, data=PDF, content_type="application/pdf", confirm=True):
        response = self.owner_client.post(
            self.kurl("uploads/upload-url/"),
            {
                "filename": "Guide.pdf",
                "content_type": content_type,
                "size": len(data),
                "category_id": self.category_id(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        upload = KnowledgeUpload.objects.get(pk=response.data["data"]["id"])
        self.storage.simulate_browser_put(upload.storage_key, data)
        if confirm:
            with self.captureOnCommitCallbacks(execute=True):
                result = self.owner_client.post(
                    self.kurl(f"uploads/{upload.id}/confirm/")
                )
            self.assertEqual(result.status_code, 200, result.content)
        upload.refresh_from_db()
        return upload

    def test_confirm_queues_indexing_and_stores_the_extracted_text(self):
        self.document_parser.markdown = "# Guide\n\nText"
        upload = self.make_upload()
        self.assertEqual(upload.index_status, IndexStatus.INDEXED)
        self.assertEqual(upload.index_error, "")
        self.assertIsNotNone(upload.indexed_at)
        self.assertEqual(self.storage.read(upload.extracted_key), b"# Guide\n\nText")
        self.assertEqual(self.document_parser.calls, [(len(PDF), "application/pdf")])

    def test_unconfirmed_uploads_are_not_indexed(self):
        upload = self.make_upload(confirm=False)
        self.assertFalse(upload_index_service.index_upload(upload.id))
        upload.refresh_from_db()
        self.assertEqual(upload.index_status, IndexStatus.PENDING)
        self.assertEqual(self.document_parser.calls, [])

    def test_page_count_comes_from_numbered_pages(self):
        self.document_parser.parse = mock.Mock(
            return_value=ParsedDocument(
                pages=(ParsedPage(1, "a"), ParsedPage(2, "b"), ParsedPage(5, "c"))
            )
        )
        self.assertEqual(self.make_upload().page_count, 5)

    def test_document_errors_fail_the_upload_without_retry(self):
        for error in (DocumentCorruptError(), DocumentEmptyError()):
            self.document_parser.fail_with = error
            upload = self.make_upload()
            self.assertEqual(
                (upload.index_status, upload.index_error, upload.extracted_key),
                (IndexStatus.FAILED, error.code, ""),
            )
        self.assertEqual(len(self.document_parser.calls), 2)  # one try each

    def test_unexpected_errors_go_back_to_pending_and_are_retried(self):
        self.document_parser.parse = mock.Mock(side_effect=RuntimeError("boom"))
        upload = self.make_upload(confirm=False)
        KnowledgeUpload.objects.filter(pk=upload.id).update(status="ready")
        with (
            mock.patch.object(
                tasks.index_upload, "retry", side_effect=Retry()
            ) as retry,
            self.assertRaises(Retry),
        ):  # the first failure schedules a retry, 60 seconds out
            tasks.index_upload.run(str(upload.id))
        self.assertEqual(retry.call_args.kwargs["countdown"], 60)
        upload.refresh_from_db()
        self.assertEqual(upload.index_status, IndexStatus.PENDING)  # claimable again

        self.document_parser.parse = mock.Mock(
            return_value=ParsedDocument(pages=(ParsedPage(None, "ok"),))
        )
        tasks.index_upload.run(str(upload.id))  # the retry succeeds
        upload.refresh_from_db()
        self.assertEqual(upload.index_status, IndexStatus.INDEXED)

    def test_the_last_retry_marks_the_upload_failed(self):
        self.document_parser.parse = mock.Mock(side_effect=RuntimeError("boom"))
        upload = self.make_upload(confirm=False)
        KnowledgeUpload.objects.filter(pk=upload.id).update(status="ready")
        tasks.index_upload.push_request(retries=tasks.index_upload.max_retries)
        try:
            with self.assertRaises(RuntimeError):
                tasks.index_upload.run(str(upload.id))
        finally:
            tasks.index_upload.pop_request()
        upload.refresh_from_db()
        self.assertEqual(
            (upload.index_status, upload.index_error),
            (IndexStatus.FAILED, "index_failed"),
        )

    def test_a_running_or_finished_upload_is_not_claimed_again(self):
        upload = self.make_upload()
        self.assertFalse(upload_index_service.index_upload(upload.id))  # INDEXED
        self.assertEqual(len(self.document_parser.calls), 1)
        self.assertTrue(upload_index_service.index_upload(upload.id, force=True))
        self.assertEqual(len(self.document_parser.calls), 2)

        KnowledgeUpload.objects.filter(pk=upload.id).update(
            index_status=IndexStatus.INDEXING, updated_at=timezone.now()
        )
        self.assertFalse(upload_index_service.index_upload(upload.id, force=True))
        KnowledgeUpload.objects.filter(pk=upload.id).update(
            updated_at=timezone.now() - timedelta(hours=1)
        )  # the worker died long ago
        self.assertTrue(upload_index_service.index_upload(upload.id))

    def test_deleting_removes_the_extracted_text_and_it_never_counts_as_quota(self):
        upload = self.make_upload()
        key = upload.extracted_key
        self.assertIn(key, self.storage.objects)
        self.assertEqual(self.used(), len(PDF))
        upload_service.delete_upload(self.owner, self.workspace_id, upload.id)
        self.assertNotIn(key, self.storage.objects)
        self.assertEqual(self.used(), 0)

    def test_purge_removes_the_extracted_text_too(self):
        upload = self.make_upload()
        upload_service.purge_workspace_objects(self.workspace_id)
        self.assertNotIn(upload.extracted_key, self.storage.objects)
        self.assertNotIn(upload.storage_key, self.storage.objects)

    def test_upload_deleted_while_reading_leaves_no_object(self):
        upload = self.make_upload(confirm=False)
        upload.status = "ready"
        upload.save(update_fields=["status"])

        def delete_then_return(data, content_type):
            KnowledgeUpload.objects.filter(pk=upload.id).delete()
            return ParsedDocument(pages=(ParsedPage(None, "text"),))

        self.document_parser.parse = delete_then_return
        self.assertFalse(upload_index_service.index_upload(upload.id))
        self.assertFalse(
            [key for key in self.storage.objects if key.endswith(".extracted.md")]
        )

    def test_sweeper_requeues_only_old_waiting_uploads(self):
        fresh = self.make_upload(confirm=False)
        old = self.make_upload(confirm=False)
        for upload in (fresh, old):
            KnowledgeUpload.objects.filter(pk=upload.id).update(status="ready")
        KnowledgeUpload.objects.filter(pk=old.id).update(
            updated_at=timezone.now() - timedelta(hours=1)
        )
        self.assertEqual(tasks.requeue_unindexed_uploads(), 1)
        old.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual(old.index_status, IndexStatus.INDEXED)
        self.assertEqual(fresh.index_status, IndexStatus.PENDING)

    def test_responses_show_the_index_state(self):
        upload = self.make_upload()
        item = self.member_client.get(self.kurl("uploads/")).data["data"]["items"][0]
        self.assertEqual(item["id"], str(upload.id))
        self.assertEqual(item["index_status"], "indexed")
        self.assertIsNone(item["index_error"])
        self.assertIsNotNone(item["indexed_at"])
        self.document_parser.fail_with = DocumentCorruptError()
        self.make_upload()
        items = self.member_client.get(self.kurl("uploads/")).data["data"]["items"]
        self.assertEqual(
            sorted((i["index_status"], i["index_error"]) for i in items),
            [("failed", "document_corrupt"), ("indexed", None)],
        )

    def test_reindex_command_requeues_uploads(self):
        upload = self.make_upload()
        out = StringIO()
        call_command("reindex_knowledge", "--uploads", "--dry-run", stdout=out)
        self.assertIn("would queue 1 uploads", out.getvalue())
        self.assertEqual(len(self.document_parser.calls), 1)
        out = StringIO()
        call_command("reindex_knowledge", "--uploads", stdout=out)
        self.assertIn("queued 1 uploads", out.getvalue())
        self.assertEqual(len(self.document_parser.calls), 2)  # forced re-read
        upload.refresh_from_db()
        self.assertEqual(upload.index_status, IndexStatus.INDEXED)
