from tickets.models import Ticket, TicketEvent, TicketMessage
from tickets.tests.base import TicketTestCase


class MessageTests(TicketTestCase):
    def setUp(self):
        super().setUp()
        self.tid = self.new_ticket()["id"]

    def post(self, body, visibility, client=None):
        return (client or self.member_client).post(
            self.turl(f"{self.tid}/messages/"),
            {"body": body, "visibility": visibility},
            format="json",
        )

    def test_public_reply_is_stored_and_queued_for_email(self):
        response = self.post("We are on it.", "public")
        self.assertEqual(response.status_code, 201)
        data = response.data["data"]
        self.assertEqual(
            (
                data["visibility"],
                data["direction"],
                data["delivery_status"],
                data["author_type"],
            ),
            ("public", "outbound", "queued", "agent"),
        )
        self.assertEqual(data["author"]["display_name"], "member")
        message = TicketMessage.objects.get(pk=data["id"])
        self.assertEqual(message.sent_from_user, self.member)
        ticket = Ticket.objects.get()
        self.assertIsNotNone(ticket.last_agent_reply_at)
        self.assertFalse(ticket.waiting_for_reply)

    def test_internal_note_is_internal_with_no_delivery(self):
        data = self.post("Customer is VIP", "internal").data["data"]
        self.assertEqual(
            (data["visibility"], data["direction"], data["delivery_status"]),
            ("internal", "internal", None),
        )
        ticket = Ticket.objects.get()
        self.assertIsNone(ticket.last_agent_reply_at)
        self.assertTrue(ticket.waiting_for_reply)  # a note does not answer the customer

    def test_history_holds_the_event_but_never_the_body(self):
        self.post("secret internal text", "internal")
        self.post("public text", "public")
        events = list(
            TicketEvent.objects.filter(
                event_type__in=["internal_note_added", "public_reply_added"]
            )
        )
        self.assertEqual(
            {e.event_type for e in events},
            {"internal_note_added", "public_reply_added"},
        )
        self.assertNotIn("secret internal text", str([e.metadata for e in events]))

    def test_list_includes_everything_in_order_for_agents(self):
        self.post("note", "internal")
        self.post("reply", "public")
        items = self.owner_client.get(self.turl(f"{self.tid}/messages/")).data["data"][
            "items"
        ]
        self.assertEqual(
            [i["visibility"] for i in items], ["public", "internal", "public"]
        )
        self.assertEqual(items[0]["author_type"], "customer")

    def test_messages_cannot_be_edited_or_deleted(self):
        message_id = self.post("hi", "public").data["data"]["id"]
        url = self.turl(f"{self.tid}/messages/{message_id}/")
        for method in ("patch", "put", "delete"):
            self.assertEqual(
                getattr(self.member_client, method)(url).status_code, 404, method
            )
        self.assertEqual(
            self.member_client.patch(
                self.turl(f"{self.tid}/messages/"), {}, format="json"
            ).status_code,
            405,
        )

    def test_validation(self):
        for body in (
            {},
            {"body": "x"},
            {"visibility": "public"},
            {"body": "", "visibility": "public"},
            {"body": "   ", "visibility": "internal"},
            {"body": "x" * 20001, "visibility": "public"},
            {"body": "x", "visibility": "secret"},
            {"body": "x", "visibility": "public", "author_type": "customer"},
        ):
            response = self.member_client.post(
                self.turl(f"{self.tid}/messages/"), body, format="json"
            )
            self.assertEqual(response.status_code, 400, body)
        self.assertEqual(TicketMessage.objects.count(), 1)

    def test_html_is_stored_as_plain_text_not_interpreted(self):
        text = "<script>alert(1)</script>"
        data = self.post(text, "public").data["data"]
        self.assertEqual(
            data["body"], text
        )  # returned as data; clients must render it as text

    def test_ticket_status_is_not_changed_by_replies(self):
        self.post("hello", "public")
        self.assertEqual(Ticket.objects.get().status, "open")
