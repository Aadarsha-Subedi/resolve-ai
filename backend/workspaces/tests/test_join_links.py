import logging
from datetime import timedelta
from unittest import mock

from django.utils import timezone
from rest_framework.test import APIClient

from common.throttling.scoped import IPScopedThrottle
from workspaces.constants.roles import MembershipStatus, Role
from workspaces.models import Workspace, WorkspaceJoinLink, WorkspaceMembership
from workspaces.tests.base import WorkspaceTestCase

REDEEM = "/api/join-links/redeem/"


class JoinLinkManagementTests(WorkspaceTestCase):
    def issue(self, workspace_id, body=None, client=None):
        client = client or self.owner_client
        return client.post(
            self.url(workspace_id, "join-link/"), body or {}, format="json"
        )

    def test_default_expiry_is_one_hour_and_token_is_hashed(self):
        workspace_id = self.create_workspace()["id"]
        response = self.issue(workspace_id)
        self.assertEqual(response.status_code, 201)
        data = response.data["data"]
        link = WorkspaceJoinLink.objects.get()
        lifetime = link.expires_at - link.created_at
        self.assertAlmostEqual(lifetime.total_seconds(), 3600, delta=5)
        self.assertNotEqual(link.token_hash, data["token"])
        self.assertEqual(len(link.token_hash), 64)
        self.assertTrue(data["url"].endswith("/join/" + data["token"]))
        self.assertNotIn(data["token"], str(WorkspaceJoinLink.objects.values()))

    def test_expiry_choices(self):
        workspace_id = self.create_workspace()["id"]
        for choice, seconds in (("1h", 3600), ("1d", 86400), ("7d", 604800)):
            self.issue(workspace_id, {"expires_in": choice})
            link = WorkspaceJoinLink.objects.get(revoked_at__isnull=True)
            self.assertAlmostEqual(
                (link.expires_at - link.created_at).total_seconds(), seconds, delta=5
            )
        self.assertEqual(
            self.issue(workspace_id, {"expires_in": "30d"}).status_code, 400
        )

    def test_get_returns_metadata_without_token(self):
        workspace_id = self.create_workspace()["id"]
        self.assertEqual(
            self.owner_client.get(self.url(workspace_id, "join-link/")).data["data"],
            {"active": False},
        )
        token = self.issue(workspace_id).data["data"]["token"]
        data = self.owner_client.get(self.url(workspace_id, "join-link/")).data["data"]
        self.assertTrue(data["active"])
        self.assertNotIn(token, str(data))
        self.assertNotIn("token", data)

    def test_member_cannot_manage_link(self):
        workspace_id = self.workspace_with_member()
        self.assertEqual(
            self.issue(workspace_id, client=self.member_client).status_code, 403
        )
        self.assertEqual(
            self.member_client.get(self.url(workspace_id, "join-link/")).status_code,
            403,
        )
        self.assertEqual(
            self.member_client.delete(self.url(workspace_id, "join-link/")).status_code,
            403,
        )

    def test_rotating_invalidates_previous_link(self):
        workspace_id = self.create_workspace()["id"]
        old = self.issue(workspace_id).data["data"]["token"]
        new = self.issue(workspace_id).data["data"]["token"]
        self.assertNotEqual(old, new)
        self.assertEqual(
            self.stranger_client.post(
                REDEEM, {"token": old}, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.stranger_client.post(
                REDEEM, {"token": new}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(
            WorkspaceJoinLink.objects.filter(revoked_at__isnull=True).count(), 1
        )

    def test_revoke(self):
        workspace_id = self.create_workspace()["id"]
        token = self.issue(workspace_id).data["data"]["token"]
        self.assertEqual(
            self.owner_client.delete(self.url(workspace_id, "join-link/")).status_code,
            200,
        )
        self.assertEqual(
            self.stranger_client.post(
                REDEEM, {"token": token}, format="json"
            ).status_code,
            404,
        )
        self.assertFalse(
            self.owner_client.get(self.url(workspace_id, "join-link/")).data["data"][
                "active"
            ]
        )


class RedeemTests(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        self.workspace_id = self.create_workspace()["id"]
        self.token = self.owner_client.post(
            self.url(self.workspace_id, "join-link/"), {}, format="json"
        ).data["data"]["token"]

    def redeem(self, client, token=None):
        return client.post(REDEEM, {"token": token or self.token}, format="json")

    def test_redeem_creates_member_directly(self):
        response = self.redeem(self.stranger_client)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["meta"], {"joined": True})
        self.assertEqual(response.data["data"]["role"], "member")
        row = WorkspaceMembership.objects.get(user=self.stranger)
        self.assertEqual((row.role, row.status), (Role.MEMBER, MembershipStatus.ACTIVE))

    def test_link_is_reusable_until_expiry(self):
        self.redeem(self.stranger_client)
        self.assertEqual(self.redeem(self.member_client).status_code, 200)

    def test_redeeming_twice_is_idempotent(self):
        self.redeem(self.stranger_client)
        again = self.redeem(self.stranger_client)
        self.assertEqual(
            (again.status_code, again.data["meta"]), (200, {"joined": False})
        )
        self.assertEqual(
            WorkspaceMembership.objects.filter(user=self.stranger).count(), 1
        )

    def test_owner_redeeming_keeps_owner_role(self):
        again = self.redeem(self.owner_client)
        self.assertEqual(again.data["data"]["role"], "owner")

    def test_removed_member_can_rejoin_as_member(self):
        self.redeem(self.stranger_client)
        self.owner_client.delete(
            self.url(self.workspace_id, f"members/{self.stranger.id}/")
        )
        response = self.redeem(self.stranger_client)
        self.assertEqual(response.data["meta"], {"joined": True})
        self.assertEqual(
            WorkspaceMembership.objects.get(user=self.stranger).role, Role.MEMBER
        )

    def test_expired_link_is_rejected_with_generic_error(self):
        WorkspaceJoinLink.objects.update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        response = self.redeem(self.stranger_client)
        self.assertEqual(
            (response.status_code, response.data["code"]), (404, "join_link_invalid")
        )
        self.assertFalse(
            WorkspaceMembership.objects.filter(user=self.stranger).exists()
        )

    def test_unknown_expired_revoked_and_deleted_look_identical(self):
        unknown = self.redeem(self.stranger_client, "x" * 43)
        WorkspaceJoinLink.objects.update(revoked_at=timezone.now())
        revoked = self.redeem(self.stranger_client)
        self.assertEqual(unknown.data["message"], revoked.data["message"])
        self.assertEqual(unknown.status_code, revoked.status_code)

    def test_deleted_workspace_link_is_rejected(self):
        self.owner_client.delete(self.url(self.workspace_id))
        self.assertEqual(self.redeem(self.stranger_client).status_code, 404)

    def test_requires_authentication_and_valid_body(self):
        self.assertEqual(
            APIClient().post(REDEEM, {"token": self.token}, format="json").status_code,
            401,
        )
        for body in ({}, {"token": ""}, {"token": "a", "extra": 1}):
            self.assertEqual(
                self.stranger_client.post(REDEEM, body, format="json").status_code,
                400,
                body,
            )

    def test_redemption_is_throttled_per_ip(self):
        rates = {**IPScopedThrottle.THROTTLE_RATES, "join_link": "2/min"}
        with mock.patch.object(IPScopedThrottle, "THROTTLE_RATES", rates):
            codes = [
                self.redeem(self.stranger_client, "bad").status_code for _ in range(3)
            ]
            other_user_same_ip = self.redeem(self.member_client, "bad").status_code
        self.assertEqual(codes, [404, 404, 429])
        self.assertEqual(other_user_same_ip, 429)

    def test_raw_token_never_logged(self):
        with self.assertLogs("request", level=logging.INFO) as captured:
            self.redeem(self.stranger_client)
            self.owner_client.post(
                self.url(self.workspace_id, "join-link/"), {}, format="json"
            )
        text = "\n".join(str(r.__dict__) for r in captured.records)
        self.assertNotIn(self.token, text)
        self.assertIn("REDACTED", text)

    def test_workspace_remains_isolated_after_join(self):
        other = self.create_workspace(client=self.owner_client, name="Other")["id"]
        self.redeem(self.stranger_client)
        self.assertEqual(self.stranger_client.get(self.url(other)).status_code, 404)
        self.assertEqual(Workspace.objects.count(), 2)
