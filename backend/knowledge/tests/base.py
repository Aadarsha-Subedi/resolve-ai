from unittest import mock

from common.storage.memory import InMemoryStorage
from knowledge.models import KnowledgeCategory
from workspaces.tests.base import WorkspaceTestCase


class KnowledgeTestCase(WorkspaceTestCase):
    """Workspace with an owner and a member, and an in-memory storage."""

    def setUp(self):
        super().setUp()
        self.storage = InMemoryStorage()
        for target in (
            "knowledge.services.article_service.get_storage",
            "knowledge.services.upload_service.get_storage",
        ):
            patcher = mock.patch(target, return_value=self.storage)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.workspace_id = self.workspace_with_member()
        from knowledge.services import category_service

        category_service.seed_defaults(self.workspace_id)

    def kurl(self, suffix="", workspace_id=None) -> str:
        return f"/api/workspaces/{workspace_id or self.workspace_id}/knowledge/{suffix}"

    def category_id(self, name="FAQ", workspace_id=None) -> str:
        return str(
            KnowledgeCategory.objects.get(
                workspace_id=workspace_id or self.workspace_id, name=name
            ).id
        )

    def create_article(
        self, client=None, title="Reset password", content="Click reset.", **extra
    ):
        client = client or self.owner_client
        response = client.post(
            self.kurl("articles/"),
            {"title": title, "content": content, **extra},
            format="json",
        )
        assert response.status_code == 201, response.content
        return response.data["data"]

    def used(self) -> int:
        return self.owner_client.get(self.kurl("storage/")).data["data"]["used_bytes"]
