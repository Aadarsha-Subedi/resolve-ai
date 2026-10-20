from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from common.exception.domain import PayloadTooLargeException
from knowledge.models import KnowledgeArticle, KnowledgeCategory, KnowledgeUpload
from knowledge.services import quota_service
from knowledge.tests.base import KnowledgeTestCase
from workspaces.models import Workspace
from workspaces.services import workspace_service


class WorkspacePurgeTests(KnowledgeTestCase):
    def test_purging_a_workspace_removes_all_its_stored_objects(self):
        article = self.create_article(content="x" * 50)
        upload = self.owner_client.post(
            self.kurl("uploads/upload-url/"),
            {"filename": "a.txt", "content_type": "text/plain", "size": 5},
            format="json",
        ).data["data"]
        upload_key = KnowledgeUpload.objects.get(pk=upload["id"]).storage_key
        self.storage.simulate_browser_put(upload_key, b"hello")
        keep = self.storage
        self.assertEqual(len(keep.objects), 2)

        self.owner_client.delete(f"/api/workspaces/{self.workspace_id}/")
        Workspace.all_objects.filter(pk=self.workspace_id).update(
            deleted_at=timezone.now() - timedelta(days=8)
        )
        from unittest import mock

        with mock.patch("common.storage.get_storage", return_value=self.storage):
            workspace_service.purge_due_workspaces()
        self.assertEqual(self.storage.objects, {})
        self.assertFalse(KnowledgeArticle.objects.filter(pk=article["id"]).exists())
        self.assertEqual(KnowledgeCategory.objects.count(), 0)


@override_settings(WORKSPACE_STORAGE_QUOTA_BYTES=100)
class QuotaServiceTests(KnowledgeTestCase):
    def test_reserve_is_all_or_nothing(self):
        quota_service.reserve(self.workspace_id, 60)
        with self.assertRaises(PayloadTooLargeException):
            quota_service.reserve(self.workspace_id, 41)
        quota_service.reserve(self.workspace_id, 40)
        self.assertEqual(quota_service.usage(self.workspace_id)["remaining_bytes"], 0)

    def test_release_never_goes_below_zero(self):
        quota_service.reserve(self.workspace_id, 10)
        quota_service.release(self.workspace_id, 50)
        self.assertEqual(quota_service.usage(self.workspace_id)["used_bytes"], 0)

    def test_zero_and_negative_sizes_are_noops(self):
        quota_service.reserve(self.workspace_id, 0)
        quota_service.release(self.workspace_id, 0)
        quota_service.release(self.workspace_id, -5)
        self.assertEqual(quota_service.usage(self.workspace_id)["used_bytes"], 0)
