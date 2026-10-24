from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditEvent
from email_integration.tests.base import EmailTestCase


class AuditEndpointTests(EmailTestCase):
    def setUp(self):
        super().setUp()
        self.url = f"/api/workspaces/{self.workspace_id}/audit/"
        # A small history: a ticket and its closing (member), a join link (owner).
        self.ticket = self.new_ticket()
        self.set_status(self.ticket["id"], "closed")
        self.owner_client.delete(
            f"/api/workspaces/{self.workspace_id}/members/{self.stranger.pk}/"
        ) if False else None
        self.owner_client.post(
            f"/api/workspaces/{self.workspace_id}/join-link/", {}, format="json"
        )

    def get(self, query="", client=None):
        return (client or self.owner_client).get(self.url + query)

    def actions(self, query=""):
        return [e["action"] for e in self.get(query).data["data"]["items"]]

    def test_owner_reads_the_log_newest_first(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        actions = self.actions()
        self.assertEqual(actions[0], "join_link.created")
        self.assertIn("workspace.created", actions)
        stamps = [e["created_at"] for e in response.data["data"]["items"]]
        self.assertEqual(stamps, sorted(stamps, reverse=True))

    def test_item_shape(self):
        item = next(
            e
            for e in self.get().data["data"]["items"]
            if e["action"] == "ticket.status_changed"
        )
        self.assertEqual(
            set(item), {"id", "action", "actor", "target", "metadata", "created_at"}
        )
        self.assertEqual(item["actor"], {"id": str(self.member.pk), "name": "member"})
        self.assertEqual(item["target"], {"type": "ticket", "id": self.ticket["id"]})
        self.assertEqual(item["metadata"], {"old": "open", "new": "closed"})

    def test_only_the_owner_can_read_it(self):
        self.assertEqual(self.get(client=self.member_client).status_code, 403)
        self.assertEqual(
            self.get(client=self.stranger_client).status_code, 404
        )  # not a member
        self.assertEqual(self.get(client=self.anon).status_code, 401)

    def test_a_removed_owner_loses_access_after_a_transfer(self):
        self.owner_client.post(
            f"/api/workspaces/{self.workspace_id}/transfer-ownership/",
            {"user_id": str(self.member.pk)},
            format="json",
        )
        self.assertEqual(self.get(client=self.owner_client).status_code, 403)
        self.assertEqual(self.get(client=self.member_client).status_code, 200)

    def test_filters(self):
        self.assertEqual(self.actions("?action=ticket.created"), ["ticket.created"])
        self.assertEqual(
            set(self.actions("?action_prefix=ticket.")),
            {"ticket.created", "ticket.status_changed"},
        )
        self.assertEqual(
            set(self.actions(f"?actor={self.member.pk}")),
            {"ticket.created", "ticket.status_changed"},
        )
        self.assertEqual(
            self.actions(f"?actor={self.owner.pk}&action_prefix=join_link"),
            ["join_link.created"],
        )
        self.assertEqual(
            self.actions(
                f"?target_type=ticket&target_id={self.ticket['id']}&action=ticket.created"
            ),
            ["ticket.created"],
        )
        self.assertEqual(self.actions("?action=member.removed"), [])

    def test_date_range(self):
        today = timezone.now().date()
        total = len(self.actions())
        self.assertEqual(
            len(self.actions(f"?created_from={today}&created_to={today}")), total
        )
        self.assertEqual(self.actions(f"?created_from={today + timedelta(days=1)}"), [])
        AuditEvent.objects.filter(action="workspace.created").update(
            created_at=timezone.now() - timedelta(days=10)
        )
        self.assertNotIn(
            "workspace.created",
            self.actions(f"?created_from={today - timedelta(days=1)}"),
        )
        self.assertEqual(
            self.actions(f"?created_to={today - timedelta(days=5)}"),
            ["workspace.created"],
        )

    def test_bad_filters(self):
        for query in (
            "?action=made.up",
            "?actor=nope",
            "?created_from=yesterday",
            "?created_to=2026-13-01",
        ):
            self.assertEqual(self.get(query).status_code, 400, query)

    def test_pagination(self):
        total = len(self.actions())
        page = self.get("?limit=2&offset=1")
        self.assertEqual(
            (
                len(page.data["data"]["items"]),
                page.data["meta"]["count"],
                page.data["meta"]["limit"],
            ),
            (2, total, 2),
        )
        self.assertEqual(
            self.actions("?limit=1000").__len__(), total
        )  # capped at 100, never an error

    def test_read_only_and_no_export(self):
        for method in ("post", "put", "patch", "delete"):
            self.assertEqual(
                getattr(self.owner_client, method)(self.url).status_code, 405, method
            )
        for suffix in ("export/", "csv/", "download/"):
            self.assertEqual(
                self.owner_client.get(self.url + suffix).status_code, 404, suffix
            )

    def test_other_workspaces_and_account_events_never_appear(self):
        other = self.create_workspace(
            client=self.stranger_client, name="Theirs", slug="theirs"
        )["id"]
        self.stranger_client.post(
            f"/api/workspaces/{other}/tickets/",
            {"subject": "s", "description": "d", "customer_email": "a@b.com"},
            format="json",
        )
        self.owner_client.post("/api/auth/logout-all/")
        self.owner_client.force_login(self.owner)  # logout-all ended the session
        mine = self.get().data["data"]["items"]
        self.assertTrue(all(e["action"] not in ("logout_all",) for e in mine))
        self.assertEqual(len([e for e in mine if e["action"] == "ticket.created"]), 1)
        theirs = self.stranger_client.get(f"/api/workspaces/{other}/audit/").data[
            "data"
        ]["items"]
        self.assertEqual(
            {e["action"] for e in theirs}, {"workspace.created", "ticket.created"}
        )
        self.assertEqual(
            self.owner_client.get(f"/api/workspaces/{other}/audit/").status_code, 404
        )

    def test_no_secret_or_message_text_in_the_response(self):
        token = self.owner_client.post(
            f"/api/workspaces/{self.workspace_id}/join-link/", {}, format="json"
        ).data["data"]["token"]
        body = self.get().content.decode()
        self.assertNotIn(token, body)
        for word in ("password", "refresh_token", "access_token"):
            self.assertNotIn(word, body)

    def test_deleted_actor_still_shows_by_name(self):
        from accounts.models import User

        User.objects.filter(pk=self.member.pk).delete()
        item = next(
            e
            for e in self.get().data["data"]["items"]
            if e["action"] == "ticket.created"
        )
        self.assertEqual(item["actor"], {"id": None, "name": "member"})

    def test_requests_to_the_endpoint_are_not_themselves_audited(self):
        before = AuditEvent.objects.count()
        self.get()
        self.get(client=self.member_client)
        self.assertEqual(AuditEvent.objects.count(), before)

    def test_unauthenticated_client_never_sees_anything(self):
        self.assertEqual(APIClient().get(self.url).status_code, 401)
