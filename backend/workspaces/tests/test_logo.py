from unittest import mock

from common.storage.base import DirectUploadUnsupported
from common.storage.memory import InMemoryStorage
from workspaces.models import Workspace
from workspaces.tests.base import WorkspaceTestCase


class LogoTests(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        self.storage = InMemoryStorage()
        patcher = mock.patch(
            "workspaces.services.logo_service.get_storage", return_value=self.storage
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.workspace_id = self.workspace_with_member()

    def upload_url(self, client=None, content_type="image/png", size=1000):
        client = client or self.owner_client
        return client.post(
            self.url(self.workspace_id, "logo/upload-url/"),
            {"content_type": content_type, "size": size},
            format="json",
        )

    def confirm(self, key, client=None):
        client = client or self.owner_client
        return client.put(
            self.url(self.workspace_id, "logo/"), {"key": key}, format="json"
        )

    def test_full_upload_flow(self):
        response = self.upload_url()
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertTrue(data["key"].startswith(f"workspaces/{self.workspace_id}/logo/"))
        self.assertTrue(data["key"].endswith(".png"))
        self.assertEqual(data["headers"], {"Content-Type": "image/png"})
        self.assertEqual(self.storage.presigned_puts[data["key"]], ("image/png", 1000))
        self.storage.simulate_browser_put(data["key"], b"x" * 1000)
        confirmed = self.confirm(data["key"])
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(
            confirmed.data["data"]["logo_url"], f"https://files.test/{data['key']}"
        )
        self.assertEqual(
            Workspace.objects.get(pk=self.workspace_id).logo_key, data["key"]
        )

    def test_replacing_logo_deletes_the_old_object(self):
        keys = []
        for _ in range(2):
            key = self.upload_url().data["data"]["key"]
            self.storage.simulate_browser_put(key, b"x")
            self.confirm(key)
            keys.append(key)
        self.assertNotIn(keys[0], self.storage.objects)
        self.assertIn(keys[1], self.storage.objects)

    def test_remove_logo(self):
        key = self.upload_url().data["data"]["key"]
        self.storage.simulate_browser_put(key, b"x")
        self.confirm(key)
        self.assertEqual(
            self.owner_client.delete(self.url(self.workspace_id, "logo/")).status_code,
            200,
        )
        self.assertEqual(self.storage.objects, {})
        self.assertIsNone(
            self.owner_client.get(self.url(self.workspace_id)).data["data"]["logo_url"]
        )

    def test_confirm_requires_a_real_object_in_this_workspace(self):
        self.assertEqual(
            self.confirm(
                f"workspaces/{self.workspace_id}/logo/missing.png"
            ).status_code,
            400,
        )
        other_key = "workspaces/someone-else/logo/a.png"
        self.storage.upload(other_key, b"x", "image/png")
        response = self.confirm(other_key)
        self.assertEqual(
            (response.status_code, response.data["code"]), (400, "logo_invalid")
        )
        self.assertIn(other_key, self.storage.objects)  # not ours to delete

    def test_wrong_type_or_oversized_object_is_rejected_and_deleted(self):
        for content_type, size in (("text/html", 10), ("image/png", 3 * 1024 * 1024)):
            key = f"workspaces/{self.workspace_id}/logo/bad.png"
            self.storage.upload(key, b"x" * size, content_type)
            self.assertEqual(self.confirm(key).status_code, 400)
            self.assertNotIn(key, self.storage.objects)
        self.assertEqual(Workspace.objects.get(pk=self.workspace_id).logo_key, "")

    def test_upload_url_validation(self):
        for body in (
            {"content_type": "image/gif", "size": 10},
            {"content_type": "image/png", "size": 0},
            {"content_type": "image/png", "size": 2 * 1024 * 1024 + 1},
            {"content_type": "image/png"},
        ):
            response = self.owner_client.post(
                self.url(self.workspace_id, "logo/upload-url/"), body, format="json"
            )
            self.assertEqual(response.status_code, 400, body)

    def test_member_cannot_change_logo(self):
        self.assertEqual(self.upload_url(client=self.member_client).status_code, 403)
        self.assertEqual(self.confirm("k", client=self.member_client).status_code, 403)
        self.assertEqual(
            self.member_client.delete(self.url(self.workspace_id, "logo/")).status_code,
            403,
        )

    def test_local_storage_cannot_presign(self):
        self.storage.presign_put = mock.Mock(side_effect=DirectUploadUnsupported)
        response = self.upload_url()
        self.assertEqual(
            (response.status_code, response.data["code"]),
            (503, "logo_upload_unsupported"),
        )
