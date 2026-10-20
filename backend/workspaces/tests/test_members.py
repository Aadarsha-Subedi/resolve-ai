from workspaces.constants.roles import MembershipStatus, Role
from workspaces.models import WorkspaceMembership
from workspaces.tests.base import WorkspaceTestCase


class MemberTests(WorkspaceTestCase):
    def test_members_can_list_members(self):
        workspace_id = self.workspace_with_member()
        for client in (self.owner_client, self.member_client):
            response = client.get(self.url(workspace_id, "members/"))
            self.assertEqual(response.status_code, 200)
            emails = {i["email"]: i["role"] for i in response.data["data"]["items"]}
            self.assertEqual(
                emails, {"owner@example.com": "owner", "member@example.com": "member"}
            )
        self.assertNotIn("password", str(response.data))

    def test_owner_removes_member(self):
        workspace_id = self.workspace_with_member()
        response = self.owner_client.delete(
            self.url(workspace_id, f"members/{self.member.id}/")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.member_client.get(self.url(workspace_id)).status_code, 404
        )
        listed = self.owner_client.get(self.url(workspace_id, "members/")).data["data"][
            "items"
        ]
        self.assertEqual(len(listed), 1)
        # History is kept: the row still exists, only its status changed.
        row = WorkspaceMembership.objects.get(user=self.member)
        self.assertEqual(row.status, MembershipStatus.REMOVED)

    def test_member_cannot_remove_anyone(self):
        workspace_id = self.workspace_with_member()
        response = self.member_client.delete(
            self.url(workspace_id, f"members/{self.owner.id}/")
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_cannot_be_removed(self):
        workspace_id = self.workspace_with_member()
        response = self.owner_client.delete(
            self.url(workspace_id, f"members/{self.owner.id}/")
        )
        self.assertEqual(
            (response.status_code, response.data["code"]), (409, "cannot_remove_owner")
        )

    def test_remove_unknown_member_is_404(self):
        workspace_id = self.workspace_with_member()
        response = self.owner_client.delete(
            self.url(workspace_id, f"members/{self.stranger.id}/")
        )
        self.assertEqual(response.status_code, 404)

    def test_member_leaves(self):
        workspace_id = self.workspace_with_member()
        self.assertEqual(
            self.member_client.post(self.url(workspace_id, "leave/")).status_code, 200
        )
        self.assertEqual(
            self.member_client.get(self.url(workspace_id)).status_code, 404
        )

    def test_owner_cannot_leave(self):
        workspace_id = self.workspace_with_member()
        response = self.owner_client.post(self.url(workspace_id, "leave/"))
        self.assertEqual(
            (response.status_code, response.data["code"]), (409, "owner_cannot_leave")
        )


class OwnershipTransferTests(WorkspaceTestCase):
    def transfer(self, client, workspace_id, user):
        return client.post(
            self.url(workspace_id, "transfer-ownership/"),
            {"user_id": str(user.id)},
            format="json",
        )

    def test_transfer_swaps_roles_atomically(self):
        workspace_id = self.workspace_with_member()
        response = self.transfer(self.owner_client, workspace_id, self.member)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["data"]["role"], "member"
        )  # the caller is now a member
        roles = dict(
            WorkspaceMembership.objects.filter(workspace_id=workspace_id).values_list(
                "user__email", "role"
            )
        )
        self.assertEqual(
            roles, {"owner@example.com": Role.MEMBER, "member@example.com": Role.OWNER}
        )
        owners = WorkspaceMembership.objects.filter(
            workspace_id=workspace_id, role=Role.OWNER, status=MembershipStatus.ACTIVE
        )
        self.assertEqual(owners.count(), 1)

    def test_old_owner_loses_owner_powers_new_owner_gains_them(self):
        workspace_id = self.workspace_with_member()
        self.transfer(self.owner_client, workspace_id, self.member)
        old, new = self.owner_client, self.member_client
        self.assertEqual(
            old.patch(self.url(workspace_id), {"name": "X"}, format="json").status_code,
            403,
        )
        self.assertEqual(old.delete(self.url(workspace_id)).status_code, 403)
        self.assertEqual(
            new.patch(self.url(workspace_id), {"name": "X"}, format="json").status_code,
            200,
        )
        self.assertEqual(old.post(self.url(workspace_id, "leave/")).status_code, 200)

    def test_member_cannot_transfer(self):
        workspace_id = self.workspace_with_member()
        response = self.transfer(self.member_client, workspace_id, self.member)
        self.assertEqual(response.status_code, 403)

    def test_cannot_transfer_to_self_or_non_member(self):
        workspace_id = self.workspace_with_member()
        to_self = self.transfer(self.owner_client, workspace_id, self.owner)
        self.assertEqual(
            (to_self.status_code, to_self.data["code"]), (400, "transfer_to_self")
        )
        outsider = self.transfer(self.owner_client, workspace_id, self.stranger)
        self.assertEqual(
            (outsider.status_code, outsider.data["code"]),
            (400, "transfer_target_invalid"),
        )
        removed_member = WorkspaceMembership.objects.filter(user=self.member)
        removed_member.update(status=MembershipStatus.REMOVED)
        gone = self.transfer(self.owner_client, workspace_id, self.member)
        self.assertEqual(gone.status_code, 400)
        self.assertEqual(
            WorkspaceMembership.objects.get(user=self.owner).role, Role.OWNER
        )

    def test_invalid_body(self):
        workspace_id = self.workspace_with_member()
        response = self.owner_client.post(
            self.url(workspace_id, "transfer-ownership/"),
            {"user_id": "nope"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
