from audit.tests.dashboard_base import DashboardTestCase
from tickets.models import Ticket


class SummaryTests(DashboardTestCase):
    def test_empty_workspace_returns_zeros(self):
        data = self.data()
        self.assertEqual(
            data["summary"],
            {
                "active": 0,
                "by_status": {"open": 0, "in_progress": 0, "pending": 0},
                "urgent": 0,
                "high": 0,
                "waiting_for_reply": 0,
                "created": {"current": 0, "previous": 0},
                "resolved": {"current": 0, "previous": 0},
            },
        )
        self.assertEqual(data["recent_tickets"]["items"], [])
        self.assertEqual(data["waiting"], {"total": 0, "items": []})
        self.assertEqual(data["activity"]["items"], [])

    def test_active_urgent_and_high_count_only_active_tickets(self):
        self.make(priority="urgent")  # open
        self.make(priority="urgent", status="in_progress")
        self.make(priority="urgent", status="pending")
        self.make(priority="urgent", status="resolved")
        self.make(priority="urgent", status="closed")
        self.make(priority="high")
        self.make(priority="high", status="closed")
        self.make(priority="low")
        s = self.data()["summary"]
        self.assertEqual(s["active"], 5)
        self.assertEqual(s["by_status"], {"open": 3, "in_progress": 1, "pending": 1})
        self.assertEqual(s["urgent"], 3)
        self.assertEqual(s["high"], 1)  # counted separately, not folded into urgent

    def test_waiting_for_reply_rule(self):
        now = self.ago(hours=1)
        before = self.ago(hours=3)
        self.make(last_customer_message_at=now, last_agent_reply_at=None)  # waiting
        self.make(last_customer_message_at=now, last_agent_reply_at=before)  # waiting
        self.make(last_customer_message_at=before, last_agent_reply_at=now)  # answered
        self.make(
            last_customer_message_at=now, last_agent_reply_at=now
        )  # tie: answered
        self.make(last_customer_message_at=None)  # no customer message
        self.make(last_customer_message_at=now, status="resolved")  # not active
        self.make(last_customer_message_at=now, status="closed")  # not active
        self.make(last_customer_message_at=now, status="pending")  # waiting
        s = self.data()["summary"]
        self.assertEqual(s["waiting_for_reply"], 3)
        self.assertEqual(self.data()["waiting"]["total"], 3)

    def test_created_current_against_previous_period(self):
        self.make(created_at=self.ago(days=1))
        self.make(created_at=self.ago(days=6))
        self.make(created_at=self.ago(days=8))  # previous 7d window
        self.make(created_at=self.ago(days=13))  # previous 7d window
        self.make(created_at=self.ago(days=20))  # before both
        s = self.data("?period=7d")["summary"]
        self.assertEqual(s["created"], {"current": 2, "previous": 2})

    def test_resolved_counts_by_resolved_at_not_current_status(self):
        t = self.make()
        self.set_status(t.id, "resolved")
        self.set_status(
            t.id, "closed", client=self.owner_client
        )  # still one resolution
        other = self.make()
        self.set_status(other.id, "resolved")
        self.set_status(other.id, "open")  # back to active: no longer resolved
        old = self.make()
        self.set_status(old.id, "resolved")
        Ticket.objects.filter(pk=old.pk).update(resolved_at=self.ago(days=40))
        s = self.data("?period=30d")["summary"]
        self.assertEqual(s["resolved"]["current"], 1)
        self.assertEqual(s["resolved"]["previous"], 1)  # 31 to 60 days ago


class ResolvedAtLifecycleTests(DashboardTestCase):
    def test_set_on_first_entry_kept_through_close_cleared_on_active(self):
        t = self.make()
        self.assertIsNone(Ticket.objects.get(pk=t.pk).resolved_at)
        self.set_status(t.id, "resolved")
        first = Ticket.objects.get(pk=t.pk).resolved_at
        self.assertIsNotNone(first)
        self.set_status(t.id, "closed")
        self.assertEqual(Ticket.objects.get(pk=t.pk).resolved_at, first)
        # The owner reopens a closed ticket straight to resolved: still the first entry.
        self.set_status(t.id, "resolved", client=self.owner_client)
        self.assertEqual(Ticket.objects.get(pk=t.pk).resolved_at, first)
        self.set_status(t.id, "in_progress")
        self.assertIsNone(Ticket.objects.get(pk=t.pk).resolved_at)

    def test_closing_an_active_ticket_sets_it(self):
        t = self.make()
        self.set_status(t.id, "closed")
        self.assertIsNotNone(Ticket.objects.get(pk=t.pk).resolved_at)


class ListsTests(DashboardTestCase):
    def test_recent_tickets_newest_activity_first_and_limited(self):
        a = self.make(subject="A", last_activity_at=self.ago(hours=3))
        b = self.make(subject="B", last_activity_at=self.ago(hours=1))
        c = self.make(subject="C", last_activity_at=self.ago(hours=2))
        items = self.data("?recent_limit=2")["recent_tickets"]["items"]
        self.assertEqual([i["subject"] for i in items], ["B", "C"])
        self.assertEqual(
            set(items[0]),
            {
                "id",
                "number",
                "subject",
                "customer_name",
                "status",
                "priority",
                "category",
                "waiting_for_reply",
                "created_at",
                "last_activity_at",
            },
        )
        self.assertNotEqual(a.pk, c.pk)
        self.assertEqual(b.number, items[0]["number"])

    def test_waiting_list_oldest_first_with_total(self):
        self.make(subject="new", last_customer_message_at=self.ago(hours=1))
        self.make(subject="old", last_customer_message_at=self.ago(hours=9))
        self.make(subject="mid", last_customer_message_at=self.ago(hours=4))
        waiting = self.data("?waiting_limit=2")["waiting"]
        self.assertEqual(waiting["total"], 3)
        self.assertEqual([i["subject"] for i in waiting["items"]], ["old", "mid"])
        self.assertEqual(
            set(waiting["items"][0]),
            {
                "id",
                "number",
                "subject",
                "customer_name",
                "status",
                "priority",
                "waiting_since",
            },
        )

    def test_activity_is_ticket_events_only_without_text_or_emails(self):
        t = self.make(subject="Billing question")
        self.member_client.post(
            self.turl(f"{t.id}/messages/"),
            {"body": "SECRET-BODY text for the customer", "visibility": "public"},
            format="json",
        )
        self.set_status(t.id, "in_progress")
        items = self.data()["activity"]["items"]
        self.assertTrue(items)
        self.assertEqual({i["source"] for i in items}, {"ticket"})
        self.assertEqual(items[0]["event_type"], "status_changed")
        self.assertEqual(
            (items[0]["old_value"], items[0]["new_value"]), ("open", "in_progress")
        )
        self.assertEqual(items[0]["actor"]["name"], "member")
        reply = next(i for i in items if i["event_type"] == "public_reply_added")
        self.assertIsNone(reply["old_value"])
        blob = str(self.data())
        self.assertNotIn("SECRET-BODY", blob)
        self.assertNotIn("@example.com", blob)
        self.assertNotIn("customer_email", blob)

    def test_internal_note_text_never_appears(self):
        t = self.make()
        self.member_client.post(
            self.turl(f"{t.id}/messages/"),
            {"body": "PRIVATE-NOTE", "visibility": "internal"},
            format="json",
        )
        self.assertNotIn("PRIVATE-NOTE", str(self.data()))
