from tickets.tests.base import TicketTestCase


class OverviewTests(TicketTestCase):
    def setUp(self):
        super().setUp()
        self.ticket = self.new_ticket(
            subject="Cannot log in", customer_email="jane@example.com"
        )
        self.tid = self.ticket["id"]
        self.member_client.post(
            self.turl(f"{self.tid}/messages/"),
            {"body": "Looking into it", "visibility": "public"},
            format="json",
        )
        self.member_client.post(
            self.turl(f"{self.tid}/messages/"),
            {"body": "VIP customer", "visibility": "internal"},
            format="json",
        )
        self.set_status(self.tid, "in_progress")

    def overview(self, client=None, query=""):
        return (client or self.member_client).get(
            self.turl(f"{self.tid}/overview/") + query
        )

    def test_one_call_returns_everything_the_page_needs(self):
        response = self.overview()
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(
            {"ticket", "viewer", "messages", "events", "meta", "email"}, set(data)
        )
        self.assertEqual(
            (data["ticket"]["subject"], data["ticket"]["status"]),
            ("Cannot log in", "in_progress"),
        )
        self.assertIn("description", data["ticket"])  # the detail shape
        self.assertEqual(
            [m["visibility"] for m in data["messages"]],
            ["public", "public", "internal"],
        )
        self.assertEqual([e["event_type"] for e in data["events"]][:1], ["created"])
        self.assertEqual(data["meta"]["messages_total"], 3)

    def test_matches_the_separate_endpoints(self):
        data = self.overview().data["data"]
        self.assertEqual(
            data["ticket"],
            self.member_client.get(self.turl(f"{self.tid}/")).data["data"],
        )
        self.assertEqual(
            data["messages"],
            self.member_client.get(self.turl(f"{self.tid}/messages/")).data["data"][
                "items"
            ],
        )
        self.assertEqual(
            data["events"],
            self.member_client.get(self.turl(f"{self.tid}/events/")).data["data"][
                "items"
            ],
        )

    def test_viewer_role_and_permissions(self):
        member = self.overview(self.member_client).data["data"]["viewer"]
        owner = self.overview(self.owner_client).data["data"]["viewer"]
        self.assertEqual((member["role"], owner["role"]), ("member", "owner"))
        self.assertIn("tickets.manage", member["permissions"])
        self.assertNotIn("workspace.delete", member["permissions"])
        self.assertIn("workspace.delete", owner["permissions"])
        self.assertEqual(member["permissions"], sorted(member["permissions"]))

    def test_gmail_status_block_is_the_viewers_own(self):
        email = self.overview().data["data"]["email"]
        self.assertEqual(email["status"], "not_connected")
        self.assertIn("reconnect=1", email["reconnect_path"])
        self.assertNotIn("token", str(email).lower().replace("reconnect", ""))

    def test_newest_items_are_returned_in_chronological_order(self):
        for i in range(5):
            self.member_client.post(
                self.turl(f"{self.tid}/messages/"),
                {"body": f"m{i}", "visibility": "internal"},
                format="json",
            )
        data = self.overview(query="?messages_limit=3&events_limit=1").data["data"]
        self.assertEqual([m["body"] for m in data["messages"]], ["m2", "m3", "m4"])
        self.assertEqual(
            (
                data["meta"]["messages_total"],
                data["meta"]["messages_returned"],
                data["meta"]["events_returned"],
            ),
            (8, 3, 1),
        )
        self.assertEqual(
            data["events"][0]["event_type"], "internal_note_added"
        )  # newest event only

    def test_limits_are_validated(self):
        for query in (
            "?messages_limit=0",
            "?messages_limit=101",
            "?events_limit=x",
            "?messages_limit=-1",
        ):
            self.assertEqual(self.overview(query=query).status_code, 400, query)

    def test_non_members_and_other_workspaces_get_404(self):
        self.assertEqual(self.overview(self.stranger_client).status_code, 404)
        other = self.create_workspace(
            client=self.stranger_client, name="Theirs", slug="theirs"
        )["id"]
        foreign = self.turl(f"{self.tid}/overview/", workspace_id=other)
        self.assertEqual(self.stranger_client.get(foreign).status_code, 404)

    def test_requires_authentication_and_is_read_only(self):
        self.assertEqual(
            self.anon.get(self.turl(f"{self.tid}/overview/")).status_code, 401
        )
        for method in ("post", "patch", "delete"):
            self.assertEqual(
                getattr(self.member_client, method)(
                    self.turl(f"{self.tid}/overview/")
                ).status_code,
                405,
            )

    def test_cost_does_not_grow_with_the_conversation(self):
        def queries() -> int:
            from django.db import connection
            from django.test.utils import CaptureQueriesContext

            with CaptureQueriesContext(connection) as captured:
                self.assertEqual(self.overview().status_code, 200)
            return len(captured)

        base = queries()
        for i in range(10):
            self.member_client.post(
                self.turl(f"{self.tid}/messages/"),
                {"body": f"n{i}", "visibility": "internal"},
                format="json",
            )
        self.assertLessEqual(queries(), base + 1)

    def test_unknown_ticket_is_404(self):
        url = self.turl("0192e9e0-0000-7000-8000-000000000001/overview/")
        self.assertEqual(self.member_client.get(url).status_code, 404)
