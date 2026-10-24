from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from common.email.utils import canonical_email_key
from workspaces.models import WorkspaceInvitation, WorkspaceMembership
from workspaces.tests.base import WorkspaceTestCase


class CanonicalEmailKeyTests(SimpleTestCase):
    def test_gmail_dots_plus_and_googlemail_collapse(self):
        same = [
            "xy@gmail.com",
            "x.y@gmail.com",
            "X.Y+news@Gmail.com",
            "xy@googlemail.com",
            " x.y+a+b@gmail.com ",
        ]
        self.assertEqual({canonical_email_key(e) for e in same}, {"xy@gmail.com"})

    def test_dot_and_plus_are_different_mailboxes(self):
        # x.y is mailbox "xy"; x+y is mailbox "x".
        self.assertEqual(canonical_email_key("x.y@gmail.com"), "xy@gmail.com")
        self.assertEqual(canonical_email_key("x+y@gmail.com"), "x@gmail.com")
        self.assertNotEqual(
            canonical_email_key("x.y@gmail.com"), canonical_email_key("x+y@gmail.com")
        )

    def test_other_domains_only_lowercase(self):
        self.assertEqual(canonical_email_key("A.B+c@Example.com"), "a.b+c@example.com")
        self.assertNotEqual(
            canonical_email_key("a.b@example.com"),
            canonical_email_key("ab@example.com"),
        )


class InvitationTests(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        self.workspace_id = self.workspace_with_member()
        self.guest = self.make_user("xy@gmail.com")
        self.guest_client = self.client_for(self.guest)

    def invite(self, emails, client=None):
        client = client or self.owner_client
        return client.post(
            self.url(self.workspace_id, "invitations/"),
            {"emails": emails},
            format="json",
        )

    def outcomes(self, response):
        return {i["email"]: i["outcome"] for i in response.data["data"]["items"]}

    def test_invite_one_or_many(self):
        response = self.invite(["a@example.com", "B@Example.com", "xy@gmail.com"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.outcomes(response),
            {
                "a@example.com": "created",
                "b@example.com": "created",
                "xy@gmail.com": "created",
            },
        )
        invitation = WorkspaceInvitation.objects.get(email="a@example.com")
        self.assertAlmostEqual(
            (invitation.expires_at - invitation.created_at).total_seconds(),
            7 * 86400,
            delta=5,
        )

    def test_same_gmail_mailbox_is_one_invitation(self):
        response = self.invite(
            ["x.y@gmail.com", "xy+news@gmail.com", "XY@googlemail.com"]
        )
        self.assertEqual(WorkspaceInvitation.objects.count(), 1)
        self.assertEqual(self.outcomes(response), {"x.y@gmail.com": "created"})
        again = self.invite(["xy@gmail.com"])
        self.assertEqual(self.outcomes(again), {"xy@gmail.com": "already_invited"})
        self.assertEqual(WorkspaceInvitation.objects.count(), 1)

    def test_other_domains_distinguish_dots(self):
        self.invite(["a.b@example.com", "ab@example.com"])
        self.assertEqual(WorkspaceInvitation.objects.count(), 2)

    def test_existing_member_is_reported_not_invited(self):
        response = self.invite(["MEMBER@example.com", "owner@example.com"])
        self.assertEqual(set(self.outcomes(response).values()), {"already_member"})
        self.assertEqual(WorkspaceInvitation.objects.count(), 0)

    def test_validation(self):
        for body in (
            {},
            {"emails": []},
            {"emails": ["not-an-email"]},
            {"emails": ["a@example.com"] * 21},
            {"emails": "a@example.com"},
        ):
            response = self.owner_client.post(
                self.url(self.workspace_id, "invitations/"), body, format="json"
            )
            self.assertEqual(response.status_code, 400, body)
        too_many = [f"u{i}@example.com" for i in range(21)]
        self.assertEqual(self.invite(too_many).status_code, 400)

    def test_member_cannot_invite_list_or_revoke(self):
        self.invite(["a@example.com"])
        invitation = WorkspaceInvitation.objects.get()
        self.assertEqual(
            self.invite(["b@example.com"], client=self.member_client).status_code, 403
        )
        self.assertEqual(
            self.member_client.get(
                self.url(self.workspace_id, "invitations/")
            ).status_code,
            403,
        )
        self.assertEqual(
            self.member_client.delete(
                self.url(self.workspace_id, f"invitations/{invitation.id}/")
            ).status_code,
            403,
        )

    def test_owner_lists_and_revokes(self):
        self.invite(["a@example.com", "b@example.com"])
        listed = self.owner_client.get(self.url(self.workspace_id, "invitations/"))
        self.assertEqual(listed.data["meta"]["count"], 2)
        invitation = WorkspaceInvitation.objects.get(email="a@example.com")
        revoke = self.owner_client.delete(
            self.url(self.workspace_id, f"invitations/{invitation.id}/")
        )
        self.assertEqual(revoke.status_code, 200)
        self.assertEqual(
            self.owner_client.get(self.url(self.workspace_id, "invitations/")).data[
                "meta"
            ]["count"],
            1,
        )
        again = self.owner_client.delete(
            self.url(self.workspace_id, f"invitations/{invitation.id}/")
        )
        self.assertEqual(again.status_code, 404)

    def test_revoked_mailbox_can_be_invited_again(self):
        self.invite(["a@example.com"])
        WorkspaceInvitation.objects.update(closed_at=timezone.now())
        response = self.invite(["a@example.com"])
        self.assertEqual(self.outcomes(response), {"a@example.com": "created"})

    def test_expired_invitation_is_replaced_by_a_new_one(self):
        self.invite(["a@example.com"])
        WorkspaceInvitation.objects.update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        response = self.invite(["a@example.com"])
        self.assertEqual(self.outcomes(response), {"a@example.com": "created"})
        self.assertEqual(
            WorkspaceInvitation.objects.filter(closed_at__isnull=True).count(), 1
        )

    def test_invited_account_sees_and_accepts_only_its_own(self):
        self.invite(["x.y+promo@gmail.com", "other@example.com"])
        mine = self.guest_client.get("/api/invitations/")
        self.assertEqual(mine.data["meta"]["count"], 1)
        item = mine.data["data"]["items"][0]
        self.assertEqual(item["workspace"]["id"], self.workspace_id)
        self.assertNotIn("email", item)
        accept = self.guest_client.post(f"/api/invitations/{item['id']}/accept/")
        self.assertEqual(accept.status_code, 200)
        self.assertEqual(accept.data["data"]["role"], "member")
        self.assertTrue(
            WorkspaceMembership.objects.filter(
                user=self.guest, workspace_id=self.workspace_id
            ).exists()
        )
        self.assertEqual(
            self.guest_client.get(self.url(self.workspace_id)).status_code, 200
        )

    def test_someone_else_cannot_accept_or_decline(self):
        self.invite(["xy@gmail.com"])
        invitation = WorkspaceInvitation.objects.get()
        for action in ("accept", "decline"):
            response = self.stranger_client.post(
                f"/api/invitations/{invitation.id}/{action}/"
            )
            self.assertEqual(response.status_code, 404, action)
        self.assertEqual(
            self.stranger_client.get("/api/invitations/").data["meta"]["count"], 0
        )

    def test_accept_twice_expired_and_revoked_are_refused(self):
        self.invite(["xy@gmail.com"])
        invitation = WorkspaceInvitation.objects.get()
        path = f"/api/invitations/{invitation.id}/accept/"
        self.assertEqual(self.guest_client.post(path).status_code, 200)
        again = self.guest_client.post(path)
        self.assertEqual(
            (again.status_code, again.data["code"]), (409, "invitation_not_usable")
        )

        WorkspaceMembership.objects.filter(user=self.guest).delete()
        WorkspaceInvitation.objects.all().delete()
        self.invite(["xy@gmail.com"])
        invitation = WorkspaceInvitation.objects.get()
        WorkspaceInvitation.objects.update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(
            self.guest_client.post(
                f"/api/invitations/{invitation.id}/accept/"
            ).status_code,
            409,
        )
        self.assertFalse(WorkspaceMembership.objects.filter(user=self.guest).exists())

        WorkspaceInvitation.objects.update(
            expires_at=timezone.now() + timedelta(days=1), closed_at=timezone.now()
        )
        self.assertEqual(
            self.guest_client.post(
                f"/api/invitations/{invitation.id}/accept/"
            ).status_code,
            409,
        )

    def test_decline(self):
        self.invite(["xy@gmail.com"])
        invitation = WorkspaceInvitation.objects.get()
        self.assertEqual(
            self.guest_client.post(
                f"/api/invitations/{invitation.id}/decline/"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.guest_client.get("/api/invitations/").data["meta"]["count"], 0
        )
        self.assertEqual(
            self.guest_client.post(
                f"/api/invitations/{invitation.id}/accept/"
            ).status_code,
            409,
        )

    def test_deleted_workspace_invitation_is_hidden(self):
        self.invite(["xy@gmail.com"])
        self.owner_client.delete(self.url(self.workspace_id))
        self.assertEqual(
            self.guest_client.get("/api/invitations/").data["meta"]["count"], 0
        )
        invitation = WorkspaceInvitation.objects.get()
        self.assertEqual(
            self.guest_client.post(
                f"/api/invitations/{invitation.id}/accept/"
            ).status_code,
            404,
        )

    def test_removed_member_can_be_invited_back(self):
        self.owner_client.delete(
            self.url(self.workspace_id, f"members/{self.member.id}/")
        )
        self.assertEqual(
            self.outcomes(self.invite(["member@example.com"])),
            {"member@example.com": "created"},
        )
        invitation = WorkspaceInvitation.objects.get()
        self.assertEqual(
            self.member_client.post(
                f"/api/invitations/{invitation.id}/accept/"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.member_client.get(self.url(self.workspace_id)).status_code, 200
        )

    def test_invitations_do_not_cross_workspaces(self):
        other = self.create_workspace(client=self.stranger_client, name="Theirs")["id"]
        self.invite(["a@example.com"])
        response = self.stranger_client.get(self.url(other, "invitations/"))
        self.assertEqual(response.data["meta"]["count"], 0)
        invitation = WorkspaceInvitation.objects.get()
        revoke = self.stranger_client.delete(
            self.url(other, f"invitations/{invitation.id}/")
        )
        self.assertEqual(revoke.status_code, 404)
        self.assertEqual(
            WorkspaceInvitation.objects.filter(closed_at__isnull=True).count(), 1
        )
