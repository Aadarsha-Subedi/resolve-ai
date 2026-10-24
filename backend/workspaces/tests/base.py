from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from workspaces.constants.roles import Role
from workspaces.models import WorkspaceMembership


class WorkspaceTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = self.make_user("owner@example.com")
        self.member = self.make_user("member@example.com")
        self.stranger = self.make_user("stranger@example.com")
        self.owner_client = self.client_for(self.owner)
        self.member_client = self.client_for(self.member)
        self.stranger_client = self.client_for(self.stranger)

    def make_user(self, email: str) -> User:
        return User.objects.create_user(email=email, display_name=email.split("@")[0])

    def client_for(self, user: User) -> APIClient:
        client = APIClient()
        client.force_login(user)
        return client

    def create_workspace(self, client=None, name="Acme Support", **extra) -> dict:
        client = client or self.owner_client
        response = client.post(
            "/api/workspaces/", {"name": name, **extra}, format="json"
        )
        assert response.status_code == 201, response.content
        return response.data["data"]

    def workspace_with_member(self) -> str:
        """A workspace owned by `owner` that `member` has joined. Returns its id."""
        workspace_id = self.create_workspace()["id"]
        WorkspaceMembership.objects.create(
            workspace_id=workspace_id, user=self.member, role=Role.MEMBER
        )
        return workspace_id

    def url(self, workspace_id, suffix="") -> str:
        return f"/api/workspaces/{workspace_id}/{suffix}"
