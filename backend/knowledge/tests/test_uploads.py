from datetime import timedelta
from unittest import mock

from django.test import override_settings
from django.utils import timezone

from common.storage.base import DirectUploadUnsupported
from knowledge.models import KnowledgeUpload
from knowledge.services import upload_service
from knowledge.tests.base import KnowledgeTestCase

PDF = b"%PDF-1.4\n" + b"x" * 100
PDF_SIZE = len(PDF)


class UploadFlowTests(KnowledgeTestCase):
    def request_url(
        self,
        size=PDF_SIZE,
        content_type="application/pdf",
        filename="Guide.pdf",
        client=None,
    ):
        return (client or self.owner_client).post(
            self.kurl("uploads/upload-url/"),
            {
                "filename": filename,
                "content_type": content_type,
                "size": size,
                "category_id": self.category_id(),
            },
            format="json",
        )

    def upload(self, data=PDF, content_type="application/pdf", filename="Guide.pdf"):
        response = self.request_url(len(data), content_type, filename)
        assert response.status_code == 201, response.content
        body = response.data["data"]
        key = KnowledgeUpload.objects.get(pk=body["id"]).storage_key
        self.storage.simulate_browser_put(key, data)
        return body, key

    def confirm(self, upload_id, client=None):
        return (client or self.owner_client).post(
            self.kurl(f"uploads/{upload_id}/confirm/")
        )

    def test_full_flow(self):
        response = self.request_url()
        self.assertEqual(response.status_code, 201)
        body = response.data["data"]
        self.assertEqual(
            (body["status"], body["headers"]),
            ("pending", {"Content-Type": "application/pdf"}),
        )
        self.assertEqual(self.used(), len(PDF))  # space is reserved right away
        key = KnowledgeUpload.objects.get().storage_key
        self.assertTrue(
            key.startswith(f"workspaces/{self.workspace_id}/knowledge/uploads/")
        )
        self.assertEqual(
            self.storage.presigned_puts[key], ("application/pdf", len(PDF))
        )
        self.storage.simulate_browser_put(key, PDF)
        confirmed = self.confirm(body["id"])
        self.assertEqual(
            (confirmed.status_code, confirmed.data["data"]["status"]), (200, "ready")
        )
        listed = self.member_client.get(self.kurl("uploads/")).data["data"]["items"]
        self.assertEqual([u["filename"] for u in listed], ["Guide.pdf"])
        self.assertEqual(self.used(), len(PDF))

    def test_pending_uploads_are_not_listed_or_downloadable(self):
        body = self.request_url().data["data"]
        self.assertEqual(
            self.member_client.get(self.kurl("uploads/")).data["meta"]["count"], 0
        )
        self.assertEqual(
            self.member_client.get(
                self.kurl(f"uploads/{body['id']}/download/")
            ).status_code,
            404,
        )

    def test_download_url_forces_download_with_the_display_name(self):
        body, _ = self.upload(filename="Guide.pdf")
        self.confirm(body["id"])
        response = self.member_client.get(self.kurl(f"uploads/{body['id']}/download/"))
        self.assertEqual(response.status_code, 200)
        url = response.data["data"]["download_url"]
        self.assertIn("disposition=attachment", url)
        self.assertIn("filename=Guide.pdf", url)
        self.assertEqual(response.data["data"]["expires_in"], 300)

    def test_text_upload(self):
        body, _ = self.upload(b"hello", "text/plain", "notes.txt")
        self.assertEqual(self.confirm(body["id"]).status_code, 200)

    def test_declared_validation(self):
        bad = [
            {"content_type": "image/png"},
            {"content_type": "application/msword"},
            {"size": 0},
            {"size": 10 * 1024 * 1024 + 1},
        ]
        for override in bad:
            args = {"size": 10, "content_type": "application/pdf", **override}
            self.assertEqual(self.request_url(**args).status_code, 400, override)
        self.assertEqual(
            self.owner_client.post(
                self.kurl("uploads/upload-url/"), {"filename": "a.pdf"}, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(self.used(), 0)
        self.assertEqual(KnowledgeUpload.objects.count(), 0)

    def test_filename_is_cleaned(self):
        for given, expected in (
            ("../../etc/passwd", "passwd.pdf"),
            ("C:\\docs\\a:b?.pdf", "a_b_.pdf"),
            ("report", "report.pdf"),
            ("...", "document.pdf"),
            ("x" * 400 + ".pdf", "x" * 251 + ".pdf"),
        ):
            self.assertEqual(
                upload_service.clean_filename(given, "application/pdf"), expected, given
            )
        body = self.request_url(filename="../secret.pdf").data["data"]
        self.assertEqual(body["filename"], "secret.pdf")
        self.assertNotIn(
            "secret", KnowledgeUpload.objects.get().storage_key
        )  # keys never use the name

    def test_confirm_without_object_discards_and_frees_space(self):
        body = self.request_url().data["data"]
        response = self.confirm(body["id"])
        self.assertEqual(
            (response.status_code, response.data["code"]), (400, "upload_invalid")
        )
        self.assertEqual((self.used(), KnowledgeUpload.objects.count()), (0, 0))

    def test_confirm_rejects_wrong_size_wrong_type_and_fake_pdf(self):
        cases = (
            (len(PDF), PDF + b"extra", "application/pdf"),  # more bytes than declared
            (len(PDF), PDF, "text/plain"),  # different content type than signed
            (30, b"not a pdf at all" * 2, "application/pdf"),  # wrong magic bytes
        )
        for declared, data, uploaded_type in cases:
            body = self.request_url(size=declared).data["data"]
            key = KnowledgeUpload.objects.get(pk=body["id"]).storage_key
            self.storage.objects[key] = (data, uploaded_type)
            self.assertEqual(
                self.confirm(body["id"]).status_code, 400, (len(data), uploaded_type)
            )
            self.assertNotIn(key, self.storage.objects)
        self.assertEqual((self.used(), KnowledgeUpload.objects.count()), (0, 0))

    def test_confirm_twice(self):
        body, _ = self.upload()
        self.confirm(body["id"])
        again = self.confirm(body["id"])
        self.assertEqual(
            (again.status_code, again.data["code"]), (409, "upload_not_pending")
        )

    def test_delete_frees_quota_and_object(self):
        body, key = self.upload()
        self.confirm(body["id"])
        self.assertEqual(
            self.member_client.delete(self.kurl(f"uploads/{body['id']}/")).status_code,
            200,
        )
        self.assertEqual(
            (self.used(), key in self.storage.objects, KnowledgeUpload.objects.count()),
            (0, False, 0),
        )

    def test_unsupported_storage(self):
        self.storage.presign_put = mock.Mock(side_effect=DirectUploadUnsupported)
        response = self.request_url()
        self.assertEqual(
            (response.status_code, response.data["code"]), (503, "upload_unsupported")
        )
        self.assertEqual((self.used(), KnowledgeUpload.objects.count()), (0, 0))

    def test_stale_pending_uploads_are_released(self):
        stale, stale_key = self.upload()
        fresh, _ = self.upload()
        ready, ready_key = self.upload()
        self.confirm(ready["id"])
        old = timezone.now() - timedelta(hours=2)
        KnowledgeUpload.objects.filter(pk__in=[stale["id"], ready["id"]]).update(
            created_at=old
        )
        self.assertEqual(upload_service.release_stale_uploads(), 1)
        remaining = set(KnowledgeUpload.objects.values_list("pk", flat=True))
        self.assertEqual({str(p) for p in remaining}, {fresh["id"], ready["id"]})
        self.assertNotIn(stale_key, self.storage.objects)
        self.assertEqual(self.used(), 2 * len(PDF))
        self.assertIn(ready_key, self.storage.objects)


class PermissionAndIsolationTests(KnowledgeTestCase):
    def test_other_workspace_cannot_use_my_uploads(self):
        body = self.owner_client.post(
            self.kurl("uploads/upload-url/"),
            {
                "filename": "a.txt",
                "content_type": "text/plain",
                "size": 5,
                "category_id": self.category_id(),
            },
            format="json",
        ).data["data"]
        other = self.create_workspace(client=self.stranger_client, name="Theirs")["id"]
        for method, suffix in (
            ("post", "confirm/"),
            ("get", "download/"),
            ("delete", ""),
        ):
            url = self.kurl(f"uploads/{body['id']}/{suffix}", other)
            self.assertEqual(
                getattr(self.stranger_client, method)(url).status_code, 404, method
            )
        self.assertEqual(
            self.stranger_client.get(self.kurl("uploads/")).status_code, 404
        )
        self.assertEqual(KnowledgeUpload.objects.count(), 1)

    def test_every_endpoint_404s_for_non_members(self):
        for method, suffix in (
            ("get", "articles/"),
            ("get", "categories/"),
            ("get", "uploads/"),
            ("get", "storage/"),
        ):
            self.assertEqual(
                getattr(self.stranger_client, method)(self.kurl(suffix)).status_code,
                404,
                suffix,
            )
        for suffix, body in (
            ("articles/", {"title": "t", "content": "c"}),
            ("categories/", {"name": "n"}),
            (
                "uploads/upload-url/",
                {
                    "filename": "a.txt",
                    "content_type": "text/plain",
                    "size": 1,
                    "category_id": self.category_id(),
                },
            ),
        ):
            self.assertEqual(
                self.stranger_client.post(
                    self.kurl(suffix), body, format="json"
                ).status_code,
                404,
                suffix,
            )


@override_settings(WORKSPACE_STORAGE_QUOTA_BYTES=1000)
class QuotaTests(KnowledgeTestCase):
    def url_for(self, size):
        return self.owner_client.post(
            self.kurl("uploads/upload-url/"),
            {
                "filename": "a.txt",
                "content_type": "text/plain",
                "size": size,
                "category_id": self.category_id(),
            },
            format="json",
        )

    def test_usage_endpoint(self):
        self.create_article(content="x" * 300)
        usage = self.member_client.get(self.kurl("storage/")).data["data"]
        self.assertEqual(
            usage, {"used_bytes": 300, "limit_bytes": 1000, "remaining_bytes": 700}
        )

    def test_articles_and_uploads_share_one_quota(self):
        self.create_article(content="x" * 600)
        self.assertEqual(self.url_for(400).status_code, 201)  # exactly fills it
        over = self.url_for(1)
        self.assertEqual(
            (over.status_code, over.data["code"]), (413, "storage_quota_exceeded")
        )
        too_big = self.owner_client.post(
            self.kurl("articles/"), {"title": "t", "content": "y"}, format="json"
        )
        self.assertEqual(too_big.status_code, 413)
        self.assertEqual(self.used(), 1000)

    def test_growing_an_article_past_the_quota_fails_and_keeps_old_content(self):
        data = self.create_article(content="x" * 900)
        response = self.owner_client.patch(
            self.kurl(f"articles/{data['id']}/"), {"content": "y" * 1001}, format="json"
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.used(), 900)
        self.assertEqual(
            self.owner_client.get(self.kurl(f"articles/{data['id']}/")).data["data"][
                "content"
            ],
            "x" * 900,
        )

    def test_shrinking_and_deleting_free_space(self):
        data = self.create_article(content="x" * 900)
        self.owner_client.patch(
            self.kurl(f"articles/{data['id']}/"), {"content": "x" * 100}, format="json"
        )
        self.assertEqual(self.url_for(900).status_code, 201)
        self.assertEqual(self.url_for(1).status_code, 413)

    def test_failed_reservation_leaves_usage_untouched(self):
        self.create_article(content="x" * 950)
        self.url_for(100)
        self.assertEqual(self.used(), 950)

    def test_quota_is_per_workspace(self):
        self.create_article(content="x" * 1000)
        other = self.create_workspace(client=self.stranger_client, name="Theirs")["id"]
        response = self.stranger_client.post(
            self.kurl("articles/", other),
            {"title": "t", "content": "x" * 1000},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_logo_does_not_count(self):
        from workspaces.models import Workspace

        Workspace.objects.filter(pk=self.workspace_id).update(
            logo_key="workspaces/x/logo/a.png"
        )
        self.assertEqual(self.used(), 0)


class UploadCategoryTests(UploadFlowTests):
    """Every file is filed under a category of its own workspace."""

    def test_category_is_required_and_returned(self):
        no_category = self.owner_client.post(
            self.kurl("uploads/upload-url/"),
            {"filename": "a.pdf", "content_type": "application/pdf", "size": 10},
            format="json",
        )
        self.assertEqual(no_category.status_code, 400)
        body = self.request_url().data["data"]
        self.assertEqual(body["category"]["id"], self.category_id())

    def test_category_from_another_workspace_is_rejected(self):
        other = self.create_workspace(client=self.stranger_client, name="Theirs")["id"]
        from knowledge.services import category_service

        category_service.seed_defaults(other)
        response = self.owner_client.post(
            self.kurl("uploads/upload-url/"),
            {
                "filename": "a.pdf",
                "content_type": "application/pdf",
                "size": 10,
                "category_id": self.category_id(workspace_id=other),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.used(), 0)

    def test_list_filters_by_category_and_filename(self):
        faq = self.category_id()
        other = self.category_id("Billing") if self._has("Billing") else None
        body, _ = self.upload(filename="Guide.pdf")
        self.confirm(body["id"])
        listed = self.owner_client.get(self.kurl(f"uploads/?category={faq}"))
        self.assertEqual([u["id"] for u in listed.data["data"]["items"]], [body["id"]])
        none = self.owner_client.get(self.kurl("uploads/?filename=zzz"))
        self.assertEqual(none.data["data"]["items"], [])
        if other:
            empty = self.owner_client.get(self.kurl(f"uploads/?category={other}"))
            self.assertEqual(empty.data["data"]["items"], [])
        bad = self.owner_client.get(self.kurl("uploads/?category=nope"))
        self.assertEqual(bad.status_code, 400)

    def test_deleting_the_category_keeps_the_file_uncategorized(self):
        body, _ = self.upload()
        self.confirm(body["id"])
        self.owner_client.delete(self.kurl(f"categories/{self.category_id()}/"))
        upload = KnowledgeUpload.objects.get(pk=body["id"])
        self.assertIsNone(upload.category)
        listed = self.owner_client.get(self.kurl("uploads/")).data["data"]["items"]
        self.assertIsNone(listed[0]["category"])

    def _has(self, name):
        from knowledge.models import KnowledgeCategory

        return KnowledgeCategory.objects.filter(
            workspace_id=self.workspace_id, name=name
        ).exists()
