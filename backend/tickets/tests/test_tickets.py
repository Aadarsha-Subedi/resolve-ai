from datetime import timedelta

from django.utils import timezone

from tickets.models import Ticket, TicketEvent, TicketMessage
from tickets.tests.base import TicketTestCase


class CreateTicketTests(TicketTestCase):
    def test_agent_creates_ticket_with_defaults(self):
        data = self.new_ticket()
        self.assertEqual(
            (data["number"], data["status"], data["priority"], data["category"]),
            (1, "open", "medium", "general"),
        )
        self.assertEqual(
            (data["customer_email"], data["created_via"]), ("jane@example.com", "agent")
        )
        self.assertTrue(data["waiting_for_reply"])
        ticket = Ticket.objects.get()
        self.assertEqual(ticket.created_by, self.member)
        # The description is the first, customer-visible message and the first history event.
        message = TicketMessage.objects.get()
        self.assertEqual(
            (message.author_type, message.visibility, message.body_text),
            ("customer", "public", "I forgot my password."),
        )
        self.assertEqual(
            list(TicketEvent.objects.values_list("event_type", flat=True)), ["created"]
        )

    def test_numbers_are_per_workspace_and_sequential(self):
        other = self.create_workspace(
            client=self.stranger_client, name="Other", slug="other"
        )["id"]
        numbers = [self.new_ticket()["number"] for _ in range(3)]
        theirs = self.stranger_client.post(
            self.turl(workspace_id=other),
            {"subject": "s", "description": "d", "customer_email": "a@b.com"},
            format="json",
        ).data["data"]["number"]
        self.assertEqual((numbers, theirs), ([1, 2, 3], 1))

    def test_failed_creation_gives_the_number_back(self):
        self.new_ticket()
        bad = self.member_client.post(self.turl(), {"subject": "s"}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.new_ticket()["number"], 2)

    def test_validation(self):
        base = {"subject": "s", "description": "d", "customer_email": "a@b.com"}
        bad = [
            {},
            {**base, "subject": ""},
            {**base, "subject": "x" * 201},
            {**base, "description": "x" * 20001},
            {**base, "customer_email": "nope"},
            {**base, "category": "sales"},
            {**base, "priority": "critical"},
            {**base, "status": "closed"},
            {**base, "customer_name": "x" * 101},
        ]
        for body in bad:
            self.assertEqual(
                self.member_client.post(self.turl(), body, format="json").status_code,
                400,
                body,
            )
        ok = self.member_client.post(
            self.turl(),
            {
                **base,
                "description": "x" * 20000,
                "category": "billing",
                "priority": "urgent",
            },
            format="json",
        )
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(Ticket.objects.count(), 1)

    def test_numbers_have_no_gaps_even_when_a_creation_rolls_back(self):
        from django.db import transaction

        from tickets.services.numbering import next_ticket_number

        self.assertEqual(self.new_ticket()["number"], 1)
        try:
            with transaction.atomic():
                self.assertEqual(next_ticket_number(self.workspace_id), 2)
                raise RuntimeError("creation failed after the number was taken")
        except RuntimeError:
            pass
        self.assertEqual(self.new_ticket()["number"], 2)  # the number was given back


class ReadAndUpdateTests(TicketTestCase):
    def test_detail_and_list_for_all_members(self):
        data = self.new_ticket()
        for client in (self.owner_client, self.member_client):
            detail = client.get(self.turl(f"{data['id']}/")).data["data"]
            self.assertEqual(detail["description"], "I forgot my password.")
            listed = client.get(self.turl()).data
            self.assertEqual(listed["meta"]["count"], 1)
            self.assertNotIn("description", listed["data"]["items"][0])

    def test_update_fields_records_events(self):
        data = self.new_ticket()
        response = self.member_client.patch(
            self.turl(f"{data['id']}/"),
            {
                "subject": "New subject",
                "priority": "urgent",
                "category": "billing",
                "customer_name": "Jane",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.data["data"]
        self.assertEqual(
            (
                body["subject"],
                body["priority"],
                body["category"],
                body["customer_name"],
            ),
            ("New subject", "urgent", "billing", "Jane"),
        )
        events = {e.event_type: e for e in TicketEvent.objects.all()}
        self.assertEqual(
            set(events),
            {"created", "priority_changed", "category_changed", "details_changed"},
        )
        self.assertEqual(
            (
                events["priority_changed"].old_value,
                events["priority_changed"].new_value,
            ),
            ("medium", "urgent"),
        )
        self.assertEqual(
            sorted(events["details_changed"].metadata["fields"]),
            ["customer_name", "subject"],
        )

    def test_noop_patch_records_nothing(self):
        data = self.new_ticket()
        self.member_client.patch(
            self.turl(f"{data['id']}/"), {"priority": "medium"}, format="json"
        )
        self.assertEqual(TicketEvent.objects.count(), 1)

    def test_patch_validation(self):
        data = self.new_ticket()
        for body in (
            {},
            {"status": "closed"},
            {"number": 9},
            {"priority": "nope"},
            {"customer_email": "x"},
        ):
            self.assertEqual(
                self.member_client.patch(
                    self.turl(f"{data['id']}/"), body, format="json"
                ).status_code,
                400,
                body,
            )

    def test_history_lists_events_in_order(self):
        data = self.new_ticket()
        self.set_status(data["id"], "in_progress")
        events = self.member_client.get(self.turl(f"{data['id']}/events/")).data[
            "data"
        ]["items"]
        self.assertEqual(
            [e["event_type"] for e in events], ["created", "status_changed"]
        )
        self.assertEqual(
            (events[1]["old_value"], events[1]["new_value"]), ("open", "in_progress")
        )

    def test_no_delete_endpoint(self):
        data = self.new_ticket()
        self.assertEqual(
            self.owner_client.delete(self.turl(f"{data['id']}/")).status_code, 405
        )
        self.assertEqual(Ticket.objects.count(), 1)


class StatusTests(TicketTestCase):
    def test_members_move_freely_and_timestamps_follow(self):
        data = self.new_ticket()
        tid = data["id"]
        for status in ("in_progress", "pending", "open"):
            self.assertEqual(self.set_status(tid, status).status_code, 200, status)
        resolved = self.set_status(tid, "resolved").data["data"]
        self.assertIsNotNone(resolved["resolved_at"])
        self.assertIsNone(resolved["closed_at"])
        closed = self.set_status(tid, "closed").data["data"]
        self.assertEqual(closed["status"], "closed")
        self.assertIsNotNone(closed["closed_at"])
        self.assertIsNotNone(closed["resolved_at"])

    def test_member_cannot_reopen_closed_but_owner_can(self):
        tid = self.new_ticket()["id"]
        self.set_status(tid, "closed")
        for status in ("open", "in_progress", "pending", "resolved"):
            response = self.set_status(tid, status)
            self.assertEqual(
                (response.status_code, response.data["code"]),
                (403, "owner_only_reopen"),
                status,
            )
        self.assertEqual(Ticket.objects.get().status, "closed")
        reopened = self.set_status(tid, "open", client=self.owner_client)
        self.assertEqual(reopened.status_code, 200)
        self.assertIsNone(reopened.data["data"]["closed_at"])
        self.assertIsNone(reopened.data["data"]["resolved_at"])
        self.assertEqual(
            self.set_status(tid, "resolved").status_code, 200
        )  # members work again

    def test_same_status_conflicts(self):
        tid = self.new_ticket()["id"]
        response = self.set_status(tid, "open")
        self.assertEqual(
            (response.status_code, response.data["code"]), (409, "status_unchanged")
        )

    def test_invalid_status_value(self):
        tid = self.new_ticket()["id"]
        self.assertEqual(self.set_status(tid, "done").status_code, 400)


class ClosedTicketLockTests(TicketTestCase):
    def setUp(self):
        super().setUp()
        self.tid = self.new_ticket()["id"]
        self.set_status(self.tid, "closed")

    def test_members_cannot_change_protected_fields(self):
        for body in (
            {"subject": "x"},
            {"description": "x"},
            {"customer_email": "a@b.com"},
            {"customer_name": "x"},
            {"category": "billing"},
            {"priority": "high"},
        ):
            response = self.member_client.patch(
                self.turl(f"{self.tid}/"), body, format="json"
            )
            self.assertEqual(
                (response.status_code, response.data["code"]),
                (403, "ticket_closed"),
                body,
            )
        self.assertEqual(Ticket.objects.get().subject, "Cannot log in")

    def test_owner_can_still_edit_a_closed_ticket(self):
        response = self.owner_client.patch(
            self.turl(f"{self.tid}/"), {"priority": "high"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_nobody_can_send_a_public_reply_but_notes_are_allowed(self):
        for client in (self.member_client, self.owner_client):
            reply = client.post(
                self.turl(f"{self.tid}/messages/"),
                {"body": "hi", "visibility": "public"},
                format="json",
            )
            self.assertEqual(
                (reply.status_code, reply.data["code"]), (403, "ticket_closed")
            )
        note = self.member_client.post(
            self.turl(f"{self.tid}/messages/"),
            {"body": "fyi", "visibility": "internal"},
            format="json",
        )
        self.assertEqual(note.status_code, 201)


class ListFilterTests(TicketTestCase):
    def setUp(self):
        super().setUp()
        self.a = self.new_ticket(
            subject="Refund request",
            customer_email="amy@shop.com",
            customer_name="Amy",
            category="billing",
            priority="low",
        )
        self.b = self.new_ticket(
            subject="App crashes",
            customer_email="bob@shop.com",
            category="technical",
            priority="urgent",
        )
        self.c = self.new_ticket(
            subject="Invoice wrong",
            customer_email="cat@other.com",
            category="billing",
            priority="high",
        )
        self.set_status(self.b["id"], "in_progress")

    def ids(self, query):
        response = self.member_client.get(self.turl() + query)
        self.assertEqual(response.status_code, 200, response.content)
        return [i["id"] for i in response.data["data"]["items"]]

    def test_filters(self):
        self.assertEqual(set(self.ids("")), {self.a["id"], self.b["id"], self.c["id"]})
        self.assertEqual(self.ids("?status=in_progress"), [self.b["id"]])
        self.assertEqual(self.ids("?priority=high"), [self.c["id"]])
        self.assertEqual(
            set(self.ids("?category=billing")), {self.a["id"], self.c["id"]}
        )
        self.assertEqual(self.ids("?category=billing&priority=low"), [self.a["id"]])

    def test_search_is_contains_on_subject_email_and_name(self):
        self.assertEqual(self.ids("?q=refund"), [self.a["id"]])
        self.assertEqual(set(self.ids("?q=shop.com")), {self.a["id"], self.b["id"]})
        self.assertEqual(self.ids("?q=amy"), [self.a["id"]])
        self.assertEqual(self.ids("?q=nothing-matches"), [])

    def test_date_range(self):
        today = timezone.now().date()
        self.assertEqual(len(self.ids(f"?created_from={today}&created_to={today}")), 3)
        self.assertEqual(self.ids(f"?created_from={today + timedelta(days=1)}"), [])
        Ticket.objects.filter(pk=self.a["id"]).update(
            created_at=timezone.now() - timedelta(days=10)
        )
        self.assertEqual(
            set(self.ids(f"?created_from={today - timedelta(days=1)}")),
            {self.b["id"], self.c["id"]},
        )

    def test_priority_orders_by_rank_not_alphabet(self):
        self.assertEqual(
            self.ids("?ordering=-priority"), [self.b["id"], self.c["id"], self.a["id"]]
        )
        self.assertEqual(
            self.ids("?ordering=priority"), [self.a["id"], self.c["id"], self.b["id"]]
        )

    def test_other_orderings_and_pagination(self):
        self.assertEqual(
            self.ids("?ordering=number"), [self.a["id"], self.b["id"], self.c["id"]]
        )
        self.assertEqual(
            self.ids("?ordering=-number&limit=2&offset=1"), [self.b["id"], self.a["id"]]
        )
        first = self.member_client.get(self.turl() + "?limit=2").data["meta"]
        self.assertEqual((first["count"], first["limit"]), (3, 2))

    def test_default_order_is_latest_activity_first(self):
        self.member_client.post(
            self.turl(f"{self.a['id']}/messages/"),
            {"body": "hello", "visibility": "internal"},
            format="json",
        )
        self.assertEqual(self.ids("")[0], self.a["id"])

    def test_waiting_for_reply_filter(self):
        self.member_client.post(
            self.turl(f"{self.a['id']}/messages/"),
            {"body": "on it", "visibility": "public"},
            format="json",
        )
        self.assertEqual(
            set(self.ids("?waiting_for_reply=true")), {self.b["id"], self.c["id"]}
        )
        self.assertEqual(self.ids("?waiting_for_reply=false"), [self.a["id"]])

    def test_bad_filters(self):
        for query in (
            "?status=bogus",
            "?priority=x",
            "?category=sales",
            "?created_from=yesterday",
            "?ordering=customer_email",
            "?ordering=description",
        ):
            self.assertEqual(
                self.member_client.get(self.turl() + query).status_code, 400, query
            )


class IsolationTests(TicketTestCase):
    def test_other_workspace_cannot_see_or_touch_tickets(self):
        data = self.new_ticket()
        other = self.create_workspace(
            client=self.stranger_client, name="Theirs", slug="theirs"
        )["id"]
        self.assertEqual(self.stranger_client.get(self.turl()).status_code, 404)
        own = self.turl(workspace_id=other)
        self.assertEqual(self.stranger_client.get(own).data["meta"]["count"], 0)
        foreign_ticket = self.turl(
            f"{data['id']}/", workspace_id=other
        )  # right id, wrong workspace
        self.assertEqual(self.stranger_client.get(foreign_ticket).status_code, 404)
        self.assertEqual(
            self.stranger_client.patch(
                foreign_ticket, {"priority": "low"}, format="json"
            ).status_code,
            404,
        )
        for suffix, body in (
            ("status/", {"status": "closed"}),
            ("messages/", {"body": "x", "visibility": "internal"}),
        ):
            response = self.stranger_client.post(
                foreign_ticket + suffix, body, format="json"
            )
            self.assertEqual(response.status_code, 404, suffix)
        self.assertEqual(
            self.stranger_client.get(foreign_ticket + "messages/").status_code, 404
        )
        self.assertEqual(
            self.stranger_client.get(foreign_ticket + "events/").status_code, 404
        )
        self.assertEqual(Ticket.objects.get().priority, "medium")

    def test_non_member_gets_404_on_every_route(self):
        data = self.new_ticket()
        t = self.turl(f"{data['id']}/")
        calls = [
            ("get", self.turl(), None),
            (
                "post",
                self.turl(),
                {"subject": "s", "description": "d", "customer_email": "a@b.com"},
            ),
            ("get", t, None),
            ("patch", t, {"priority": "low"}),
            ("post", t + "status/", {"status": "closed"}),
            ("get", t + "messages/", None),
            ("post", t + "messages/", {"body": "x", "visibility": "public"}),
            ("get", t + "events/", None),
        ]
        for method, url, body in calls:
            response = (
                getattr(self.stranger_client, method)(url, body, format="json")
                if body is not None
                else getattr(self.stranger_client, method)(url)
            )
            self.assertEqual(response.status_code, 404, (method, url))

    def test_requires_authentication(self):
        self.assertEqual(self.anon.get(self.turl()).status_code, 401)
        self.assertEqual(
            self.anon.post(self.turl(), {}, format="json").status_code, 401
        )
