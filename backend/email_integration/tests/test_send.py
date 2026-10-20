from email_integration.clients.base import (
    GmailAuthError,
    GmailRejectedError,
    GmailTransientError,
)
from email_integration.constants.enums import ConnectionStatus
from email_integration.models import GmailConnection
from email_integration.services import send_service
from email_integration.tests.base import EmailTestCase
from tickets.models import Ticket, TicketEvent, TicketMessage


class SendReplyTests(EmailTestCase):
    def setUp(self):
        super().setUp()
        self.connect(self.member)
        self.ticket = self.new_ticket(
            subject="Cannot log in", customer_email="jane@example.com"
        )

    def test_public_reply_is_emailed_from_the_agents_own_mailbox(self):
        response = self.reply(self.ticket["id"], "We are on it.")
        self.assertEqual(response.status_code, 201)
        sent = self.gmail(self.member).sent
        self.assertEqual(len(sent), 1)
        mail = sent[0]["message"]
        self.assertEqual(mail["To"], "jane@example.com")
        self.assertIn("member@example.com", mail["From"])
        self.assertEqual(mail["Subject"], "Re: Cannot log in [#1]")
        self.assertEqual(mail.get_payload().strip(), "We are on it.")
        message = self.message(self.ticket["id"])
        self.assertEqual(
            (message.delivery_status, message.delivery_error), ("sent", "")
        )
        self.assertTrue(message.email_message_id.startswith("<"))
        self.assertEqual(
            (message.mailbox_user, message.sent_from_user), (self.member, self.member)
        )

    def test_internal_notes_are_never_emailed(self):
        self.reply(self.ticket["id"], "secret note", visibility="internal")
        self.assertEqual(self.gmail(self.member).sent, [])
        self.assertEqual(self.message(self.ticket["id"]).delivery_status, "")

    def test_no_internal_text_leaks_into_the_email(self):
        self.reply(self.ticket["id"], "internal only", visibility="internal")
        self.reply(self.ticket["id"], "public text")
        raw = self.gmail(self.member).sent[0]["raw"].decode()
        self.assertNotIn("internal only", raw)

    def test_replies_thread_together(self):
        self.reply(self.ticket["id"], "first")
        self.reply(self.ticket["id"], "second")
        first, second = self.gmail(self.member).sent
        self.assertIsNone(first["thread_id"])
        self.assertEqual(
            second["thread_id"], self.message(self.ticket["id"], 1).email_thread_id
        )
        mail = second["message"]
        first_id = self.message(self.ticket["id"], 1).email_message_id
        self.assertEqual(mail["In-Reply-To"], first_id)
        self.assertIn(first_id, mail["References"])

    def test_each_agent_replies_from_their_own_mailbox(self):
        self.connect(self.owner)
        self.reply(self.ticket["id"], "from member")
        self.reply(self.ticket["id"], "from owner", client=self.owner_client)
        self.assertEqual(len(self.gmail(self.member).sent), 1)
        self.assertEqual(len(self.gmail(self.owner).sent), 1)
        self.assertIn(
            "owner@example.com", self.gmail(self.owner).sent[0]["message"]["From"]
        )

    def test_no_gmail_connection_marks_the_reply_failed_with_an_event(self):
        ticket = self.new_ticket(
            client=self.owner_client
        )  # owner never connected Gmail
        self.reply(ticket["id"], "hello", client=self.owner_client)
        message = self.message(ticket["id"])
        self.assertEqual(
            (message.delivery_status, message.delivery_error),
            ("failed", "gmail_not_connected"),
        )
        event = TicketEvent.objects.get(
            event_type="email_delivery_failed", ticket_id=ticket["id"]
        )
        self.assertEqual(event.metadata["reason"], "gmail_not_connected")
        self.assertNotIn("hello", str(event.metadata))
        listed = self.owner_client.get(self.turl(f"{ticket['id']}/messages/")).data[
            "data"
        ]["items"]
        self.assertEqual(listed[-1]["delivery_status"], "failed")

    def test_not_connected_or_reauth_connection_cannot_send(self):
        for status in (
            ConnectionStatus.NOT_CONNECTED,
            ConnectionStatus.REAUTH_REQUIRED,
            ConnectionStatus.DISCONNECTED,
        ):
            GmailConnection.objects.filter(user=self.member).update(status=status)
            ticket = self.new_ticket()
            self.reply(ticket["id"], "hi")
            self.assertEqual(
                self.message(ticket["id"]).delivery_status, "failed", status
            )
        self.assertEqual(self.gmail(self.member).sent, [])

    def test_revoked_token_marks_reauth_required(self):
        self.gmail(self.member).fail_with = GmailAuthError()
        self.reply(self.ticket["id"], "hi")
        self.assertEqual(
            self.message(self.ticket["id"]).delivery_error, "gmail_reauth_required"
        )
        self.assertEqual(
            GmailConnection.objects.get(user=self.member).status, "reauth_required"
        )
        status = self.member_client.get("/api/email/gmail/").data["data"]
        self.assertEqual(status["status"], "reauth_required")
        self.assertIn("reconnect=1", status["reconnect_path"])

    def test_gmail_rejection_fails_permanently(self):
        self.gmail(self.member).fail_with = GmailRejectedError()
        self.reply(self.ticket["id"], "hi")
        self.assertEqual(
            self.message(self.ticket["id"]).delivery_error, "gmail_rejected"
        )

    def test_transient_errors_retry_then_fail(self):
        message_id = self.reply(self.ticket["id"], "hi").data["data"]["id"]
        TicketMessage.objects.filter(pk=message_id).update(
            delivery_status="queued", delivery_error=""
        )
        self.gmail(self.member).fail_with = GmailTransientError()
        with self.assertRaises(send_service.RetryableSendError):
            send_service.send_ticket_message(message_id)
        self.assertEqual(
            TicketMessage.objects.get(pk=message_id).delivery_status, "queued"
        )
        self.gmail(self.member).fail_with = GmailTransientError()
        send_service.send_ticket_message(message_id, final_attempt=True)
        self.assertEqual(
            TicketMessage.objects.get(pk=message_id).delivery_error, "gmail_unavailable"
        )

    def test_sending_is_idempotent(self):
        message_id = self.reply(self.ticket["id"], "hi").data["data"]["id"]
        send_service.send_ticket_message(message_id)
        send_service.send_ticket_message(message_id)
        self.assertEqual(len(self.gmail(self.member).sent), 1)

    def test_resend_a_failed_reply(self):
        self.gmail(self.member).fail_with = GmailRejectedError()
        message_id = self.reply(self.ticket["id"], "hi").data["data"]["id"]
        url = self.turl(f"{self.ticket['id']}/messages/{message_id}/resend/")
        again = self.api(self.member_client, "post", url)
        self.assertEqual(
            (again.status_code, again.data["data"]["delivery_status"]), (200, "sent")
        )
        self.assertEqual(len(self.gmail(self.member).sent), 1)
        twice = self.api(self.member_client, "post", url)
        self.assertEqual(
            (twice.status_code, twice.data["code"]), (409, "message_not_failed")
        )

    def test_only_the_sender_or_owner_can_resend(self):
        self.connect(self.owner)
        self.gmail(self.member).fail_with = GmailRejectedError()
        message_id = self.reply(self.ticket["id"], "hi").data["data"]["id"]
        url = self.turl(f"{self.ticket['id']}/messages/{message_id}/resend/")
        self.assertEqual(self.api(self.stranger_client, "post", url).status_code, 404)
        TicketMessage.objects.filter(pk=message_id).update(sent_from_user=self.owner)
        other = self.make_user("agent2@example.com")
        from workspaces.constants.roles import Role
        from workspaces.models import WorkspaceMembership

        WorkspaceMembership.objects.create(
            workspace_id=self.workspace_id, user=other, role=Role.MEMBER
        )
        self.assertEqual(self.api(self.client_for(other), "post", url).status_code, 404)

    def test_closed_ticket_reply_is_not_sent(self):
        self.set_status(self.ticket["id"], "closed")
        response = self.reply(self.ticket["id"], "hi")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.gmail(self.member).sent, [])


class PortalConfirmationTests(EmailTestCase):
    def portal_ticket(self):
        response = self.api(
            self.anon,
            "post",
            "/api/portal/acme/tickets/",
            {
                "subject": "Where is my order?",
                "description": "Nothing arrived",
                "customer_email": "cara@example.com",
                "customer_name": "Cara",
            },
        )
        self.assertEqual(response.status_code, 201)
        return Ticket.objects.get()

    def test_confirmation_is_sent_from_the_owners_mailbox(self):
        self.connect(self.owner)
        ticket = self.portal_ticket()
        mail = self.gmail(self.owner).sent[0]["message"]
        self.assertEqual(mail["To"], "cara@example.com")
        self.assertIn("owner@example.com", mail["From"])
        self.assertIn("#1", mail["Subject"])
        self.assertIn("/portal/acme", mail.get_payload())
        ticket.refresh_from_db()
        self.assertFalse(ticket.confirmation_pending)
        confirmation = TicketMessage.objects.get(ticket=ticket, author_type="system")
        self.assertEqual(
            (confirmation.delivery_status, confirmation.visibility), ("sent", "public")
        )

    def test_skipped_without_a_connected_owner(self):
        ticket = self.portal_ticket()
        self.assertEqual(self.gmail(self.owner).sent, [])
        ticket.refresh_from_db()
        self.assertFalse(ticket.confirmation_pending)
        self.assertFalse(
            TicketMessage.objects.filter(ticket=ticket, author_type="system").exists()
        )

    def test_agent_created_tickets_send_nothing(self):
        self.connect(self.owner)
        self.api(
            self.owner_client,
            "post",
            self.turl(),
            {"subject": "s", "description": "d", "customer_email": "a@b.com"},
        )
        self.assertEqual(self.gmail(self.owner).sent, [])

    def test_customer_reply_to_the_confirmation_lands_on_the_ticket(self):
        from email_integration.services import inbound_service

        connection = self.connect(self.owner)
        ticket = self.portal_ticket()
        confirmation_id = TicketMessage.objects.get(
            ticket=ticket, author_type="system"
        ).email_message_id
        fake = self.gmail(self.owner)
        gmail_id = fake.deliver(
            sender="Cara <cara@example.com>",
            in_reply_to=confirmation_id,
            body="Order #55",
        )
        report = inbound_service.manual_sync(connection)
        self.assertEqual(report.matched, 1)
        self.assertEqual(
            TicketMessage.objects.filter(ticket=ticket, author_type="customer").count(),
            2,
        )
        self.assertIn(gmail_id, fake.messages)


class OverviewEmailBlockTests(EmailTestCase):
    def test_ticket_overview_shows_the_viewers_gmail_status(self):
        ticket = self.new_ticket()
        url = self.turl(f"{ticket['id']}/overview/")
        before = self.member_client.get(url).data["data"]["email"]
        self.assertEqual(before["status"], "not_connected")
        self.connect(self.member)
        after = self.member_client.get(url).data["data"]["email"]
        self.assertEqual(
            (after["status"], after["mailbox_email"], after["reconnect_path"]),
            ("connected", "member@example.com", None),
        )
        # Each viewer sees their own connection, not their colleague's.
        self.assertEqual(
            self.owner_client.get(url).data["data"]["email"]["status"], "not_connected"
        )
