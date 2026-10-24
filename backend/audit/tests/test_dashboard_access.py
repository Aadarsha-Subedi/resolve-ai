from rest_framework.test import APIClient

from audit.tests.dashboard_base import DashboardTestCase
from workspaces.constants.roles import MembershipStatus
from workspaces.models import WorkspaceMembership


class DashboardAccessTests(DashboardTestCase):
    def test_owner_and_member_can_read(self):
        self.assertEqual(self.dash(client=self.owner_client).status_code, 200)
        self.assertEqual(self.dash(client=self.member_client).status_code, 200)

    def test_both_roles_hold_the_permission_code(self):
        from workspaces.constants.permissions import DASHBOARD_VIEW, ROLE_PERMISSIONS
        from workspaces.constants.roles import Role

        self.assertEqual(DASHBOARD_VIEW, "dashboard.view")
        self.assertIn(DASHBOARD_VIEW, ROLE_PERMISSIONS[Role.OWNER])
        self.assertIn(DASHBOARD_VIEW, ROLE_PERMISSIONS[Role.MEMBER])

    def test_anonymous_is_rejected(self):
        self.assertIn(self.dash(client=APIClient()).status_code, (401, 403))

    def test_non_member_gets_404(self):
        self.assertEqual(self.dash(client=self.stranger_client).status_code, 404)

    def test_removed_member_gets_404(self):
        self.assertEqual(self.dash().status_code, 200)
        WorkspaceMembership.objects.filter(user=self.member).update(
            status=MembershipStatus.REMOVED
        )
        self.assertEqual(self.dash().status_code, 404)

    def test_a_removed_member_is_not_served_from_the_cache(self):
        self.assertFalse(self.dash(client=self.owner_client).data["meta"]["cached"])
        self.assertTrue(self.dash(client=self.owner_client).data["meta"]["cached"])
        WorkspaceMembership.objects.filter(user=self.member).update(
            status=MembershipStatus.REMOVED
        )
        self.assertEqual(self.dash().status_code, 404)

    def test_unknown_workspace_gets_404(self):
        self.assertEqual(
            self.dash(workspace_id="0197f0a0-0000-7000-8000-000000000000").status_code,
            404,
        )

    def test_other_workspaces_tickets_never_count(self):
        other = self.create_workspace(
            client=self.stranger_client, name="Other", slug="other"
        )
        body = {
            "subject": "Secret",
            "description": "x",
            "customer_email": "c@example.com",
        }
        created = self.stranger_client.post(
            f"/api/workspaces/{other['id']}/tickets/", body, format="json"
        )
        self.assertEqual(created.status_code, 201)
        mine = self.data()
        self.assertEqual(mine["summary"]["active"], 0)
        self.assertEqual(mine["recent_tickets"]["items"], [])
        self.assertEqual(mine["activity"]["items"], [])
        self.assertEqual(mine["waiting"]["total"], 0)
        theirs = self.dash(workspace_id=other["id"], client=self.stranger_client)
        self.assertEqual(theirs.data["data"]["summary"]["active"], 1)
        # A member of one workspace cannot read the other one's dashboard.
        self.assertEqual(
            self.dash(workspace_id=other["id"], client=self.member_client).status_code,
            404,
        )

    def test_only_get_is_allowed(self):
        self.assertEqual(self.member_client.post(self.durl, {}).status_code, 405)
        self.assertEqual(self.member_client.delete(self.durl).status_code, 405)
