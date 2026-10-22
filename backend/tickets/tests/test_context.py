from django.core.cache import cache
from django.test import override_settings

from tickets.constants.enums import AuthorType, MessageDirection, MessageVisibility
from tickets.models import Ticket, TicketMessage
from tickets.tests.base import TicketTestCase

REFUND = (
    "# Refund policy\n\nYou can request a refund within 14 days of purchase for an "
    "annual plan. The refund goes back to the original payment method."
)


@override_settings(GEMINI_API_KEY="", LLM_CALL_LIMIT=100)
class TicketContextTests(TicketTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        response = self.owner_client.post(
            f"/api/workspaces/{self.workspace_id}/knowledge/articles/",
            {"title": "Refund policy", "content": REFUND},
            format="json",
        )
        self.owner_client.post(
            f"/api/workspaces/{self.workspace_id}/knowledge/articles/"
            f"{response.data['data']['id']}/publish/"
        )
        self.ticket = self.new_ticket(
            subject="Refund for annual plan",
            description="I was charged twice and want my money back.",
        )

    def message(
        self, body, author=AuthorType.CUSTOMER, visibility="public", ticket_id=None
    ):
        return TicketMessage.objects.create(
            workspace_id=self.workspace_id,
            ticket=Ticket.objects.get(pk=ticket_id or self.ticket["id"]),
            author_type=author,
            visibility=visibility,
            direction=MessageDirection.INBOUND
            if author == AuthorType.CUSTOMER
            else MessageDirection.INTERNAL,
            body_text=body,
        )

    def context(self, body=None, ticket_id=None, client=None, workspace_id=None):
        return (client or self.member_client).post(
            self.turl(f"{ticket_id or self.ticket['id']}/context/", workspace_id),
            body or {},
            format="json",
        )

    def test_whole_ticket_uses_subject_and_description(self):
        response = self.context()
        self.assertEqual(response.status_code, 200)
        terms = response.data["data"]["terms"]
        self.assertIn("annual", terms)
        self.assertIn("money", terms)

    def test_one_customer_message_is_used_alone(self):
        message = self.message("The invoice shows a zebra surcharge")
        response = self.context({"message_id": str(message.id)})
        terms = response.data["data"]["terms"]
        self.assertIn("zebra", terms)
        self.assertNotIn("annual", terms)

    def test_internal_notes_are_never_the_query(self):
        note = self.message(
            "quokka secret note", AuthorType.AGENT, MessageVisibility.INTERNAL
        )
        for body in ({}, {"message_id": str(note.id)}):
            response = self.context(body)
            if body:
                self.assertEqual(response.status_code, 404)
            else:
                self.assertNotIn("quokka", response.data["data"]["terms"])

    def test_agent_replies_and_foreign_ids_look_like_unknown_messages(self):
        reply = self.message("We are looking into it", AuthorType.AGENT)
        other = self.new_ticket(subject="Other", description="Other text here")
        elsewhere = self.message("From another ticket", ticket_id=other["id"])
        for message_id in (
            reply.id,
            elsewhere.id,
            "00000000-0000-0000-0000-000000000000",
        ):
            response = self.context({"message_id": str(message_id)})
            self.assertEqual(response.status_code, 404, message_id)

    def test_bad_bodies(self):
        self.assertEqual(self.context({"message_id": "nope"}).status_code, 400)
        self.assertEqual(self.context({"extra": 1}).status_code, 400)

    def test_access_rules(self):
        self.assertEqual(self.context(client=self.stranger_client).status_code, 404)
        self.assertEqual(
            self.context(ticket_id="00000000-0000-0000-0000-000000000000").status_code,
            404,
        )
        other_workspace = self.create_workspace(name="Other")["id"]
        self.assertEqual(self.context(workspace_id=other_workspace).status_code, 404)

    def test_returns_published_passages_for_the_ticket(self):
        response = self.context()
        titles = [r["article"]["title"] for r in response.data["data"]["results"]]
        from django.db import connection

        if connection.vendor == "postgresql":
            self.assertEqual(titles, ["Refund policy"])
