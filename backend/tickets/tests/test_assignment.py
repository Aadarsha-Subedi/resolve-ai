from django.db import connection
from django.test.utils import CaptureQueriesContext

from audit.models import AuditEvent
from tickets.models import Ticket, TicketEvent
from tickets.tests.base import TicketTestCase
from workspaces.constants.roles import MembershipStatus
from workspaces.models import WorkspaceMembership


class AssignTicketTests(TicketTestCase):
    def setUp(self):
        super().setUp()
        self.ticket = self.new_ticket()
        self.tid = self.ticket["id"]

    def assign(self, user_id, client=None, tid=None):
        return (client or self.member_client).post(
            self.turl(f"{tid or self.tid}/assignee/"),
            {"assignee": str(user_id) if user_id else None},
            format="json",
        )

    def test_member_assigns_and_unassigns(self):
        response = self.assign(self.member.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["data"]["assignee"],
            {"id": str(self.member.id), "display_name": "member"},
        )
        self.assertEqual(Ticket.objects.get().assignee, self.member)
        response = self.assign(None)
        self.assertIsNone(response.data["data"]["assignee"])
        events = TicketEvent.objects.filter(event_type="assignee_changed").order_by(
            "created_at", "id"
        )
        self.assertEqual(events.count(), 2)
        first, second = events
        self.assertIsNone(first.old_value)
        self.assertEqual(first.new_value["id"], str(self.member.id))
        self.assertEqual(second.old_value["id"], str(self.member.id))
        self.assertIsNone(second.new_value)

    def test_owner_can_assign_a_member(self):
        response = self.assign(self.member.id, client=self.owner_client)
        self.assertEqual(response.status_code, 200)

    def test_same_assignee_is_a_no_op(self):
        self.assign(self.member.id)
        self.assign(self.member.id)
        self.assertEqual(
            TicketEvent.objects.filter(event_type="assignee_changed").count(), 1
        )

    def test_assignee_must_be_an_active_member(self):
        self.assertEqual(self.assign(self.stranger.id).status_code, 400)
        self.assertEqual(self.assign(self.stranger.id).data["code"], "assignee_invalid")
        WorkspaceMembership.objects.filter(user=self.member).update(
            status=MembershipStatus.REMOVED
        )
        self.assertEqual(
            self.assign(self.member.id, client=self.owner_client).status_code, 400
        )
        self.assertIsNone(Ticket.objects.get().assignee)

    def test_non_members_get_404_and_cross_workspace_ticket_is_hidden(self):
        self.assertEqual(
            self.assign(self.member.id, client=self.stranger_client).status_code, 404
        )

    def test_closed_ticket_assignee_is_locked_for_members_not_owner(self):
        self.set_status(self.tid, "closed")
        denied = self.assign(self.member.id)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.data["code"], "ticket_closed")
        self.assertEqual(
            self.assign(self.member.id, client=self.owner_client).status_code, 200
        )

    def test_unknown_fields_and_bad_ids_rejected(self):
        response = self.member_client.post(
            self.turl(f"{self.tid}/assignee/"), {"assignee": "nope"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response = self.member_client.post(
            self.turl(f"{self.tid}/assignee/"), {}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_detail_overview_and_list_carry_the_assignee(self):
        self.assign(self.member.id)
        detail = self.member_client.get(self.turl(f"{self.tid}/")).data["data"]
        overview = self.member_client.get(self.turl(f"{self.tid}/overview/")).data[
            "data"
        ]
        listed = self.member_client.get(self.turl()).data["data"]["items"][0]
        for data in (detail, overview["ticket"], listed):
            self.assertEqual(data["assignee"]["id"], str(self.member.id))
        self.assertIn("tickets.assign", overview["viewer"]["permissions"])

    def test_assignment_is_audited_without_names(self):
        self.assign(self.member.id, client=self.owner_client)
        row = AuditEvent.objects.get(action="ticket.assignee_changed")
        self.assertEqual(row.metadata["assignee_id"], str(self.member.id))
        self.assertNotIn("member@example.com", str(row.metadata))

    def test_assigning_updates_last_activity(self):
        before = Ticket.objects.get().last_activity_at
        self.assign(self.member.id)
        self.assertGreater(Ticket.objects.get().last_activity_at, before)


class AssigneeFilterTests(TicketTestCase):
    def setUp(self):
        super().setUp()
        self.mine = self.new_ticket(subject="mine")["id"]
        self.owners = self.new_ticket(subject="owners")["id"]
        self.nobody = self.new_ticket(subject="nobody")["id"]
        for tid, user in ((self.mine, self.member), (self.owners, self.owner)):
            self.member_client.post(
                self.turl(f"{tid}/assignee/"),
                {"assignee": str(user.id)},
                format="json",
            )

    def ids(self, query, client=None):
        response = (client or self.member_client).get(self.turl(f"?assignee={query}"))
        self.assertEqual(response.status_code, 200, response.content)
        return {t["id"] for t in response.data["data"]["items"]}

    def test_me(self):
        self.assertEqual(self.ids("me"), {self.mine})
        self.assertEqual(self.ids("me", self.owner_client), {self.owners})

    def test_unassigned(self):
        self.assertEqual(self.ids("unassigned"), {self.nobody})

    def test_specific_member(self):
        self.assertEqual(self.ids(self.owner.id), {self.owners})

    def test_invalid_value_is_rejected(self):
        response = self.member_client.get(self.turl("?assignee=everyone"))
        self.assertEqual(response.status_code, 400)

    def test_list_does_not_query_per_ticket(self):
        def count():
            with CaptureQueriesContext(connection) as queries:
                self.member_client.get(self.turl())
            return len(queries)

        before = count()
        for number in range(3):
            tid = self.new_ticket(subject=f"extra {number}")["id"]
            self.member_client.post(
                self.turl(f"{tid}/assignee/"),
                {"assignee": str(self.owner.id)},
                format="json",
            )
        self.assertEqual(count(), before)


class DepartedMemberTests(TicketTestCase):
    def setUp(self):
        super().setUp()
        self.open = self.new_ticket(subject="a")["id"]
        self.pending = self.new_ticket(subject="b")["id"]
        self.closed = self.new_ticket(subject="c")["id"]
        self.set_status(self.pending, "pending")
        for tid in (self.open, self.pending, self.closed):
            self.owner_client.post(
                self.turl(f"{tid}/assignee/"),
                {"assignee": str(self.member.id)},
                format="json",
            )
        self.set_status(self.closed, "closed")

    def assignee_of(self, tid):
        return Ticket.objects.get(pk=tid).assignee

    def check(self):
        self.assertIsNone(self.assignee_of(self.open))
        self.assertIsNone(self.assignee_of(self.pending))
        self.assertEqual(self.assignee_of(self.closed), self.member)  # history kept
        event = TicketEvent.objects.filter(
            ticket_id=self.open, event_type="assignee_changed"
        ).last()
        self.assertIsNone(event.actor_user)
        self.assertEqual(event.old_value["id"], str(self.member.id))
        self.assertIsNone(event.new_value)

    def test_removed_member_loses_active_tickets(self):
        response = self.owner_client.delete(
            f"/api/workspaces/{self.workspace_id}/members/{self.member.id}/"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.check()
        self.assertEqual(
            TicketEvent.objects.filter(
                ticket_id=self.open, event_type="assignee_changed"
            )
            .last()
            .metadata["reason"],
            "member_removed",
        )

    def test_member_who_leaves_loses_active_tickets(self):
        response = self.member_client.post(
            f"/api/workspaces/{self.workspace_id}/leave/"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.check()
