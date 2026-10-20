from rest_framework.test import APIClient

from workspaces.tests.base import WorkspaceTestCase


class TicketTestCase(WorkspaceTestCase):
    """A workspace with an owner and a member, and an anonymous client for the portal."""

    def setUp(self):
        super().setUp()
        self.workspace = self.create_workspace(name="Acme Support", slug="acme")
        self.workspace_id = self.workspace["id"]
        from workspaces.constants.roles import Role
        from workspaces.models import WorkspaceMembership

        WorkspaceMembership.objects.create(
            workspace_id=self.workspace_id, user=self.member, role=Role.MEMBER
        )
        self.anon = APIClient()

    def turl(self, suffix="", workspace_id=None) -> str:
        return f"/api/workspaces/{workspace_id or self.workspace_id}/tickets/{suffix}"

    def new_ticket(self, client=None, **extra) -> dict:
        body = {
            "subject": "Cannot log in",
            "description": "I forgot my password.",
            "customer_email": "Jane@Example.com",
            **extra,
        }
        response = (client or self.member_client).post(self.turl(), body, format="json")
        assert response.status_code == 201, response.content
        return response.data["data"]

    def set_status(self, ticket_id, status, client=None):
        return (client or self.member_client).post(
            self.turl(f"{ticket_id}/status/"), {"status": status}, format="json"
        )

    def portal(self, body=None, slug="acme", client=None):
        body = {
            "subject": "Help",
            "description": "Need help",
            "customer_email": "cust@example.com",
            **(body or {}),
        }
        return (client or self.anon).post(
            f"/api/portal/{slug}/tickets/", body, format="json"
        )
