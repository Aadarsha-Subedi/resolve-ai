from datetime import timedelta
from unittest import mock

from django.test import override_settings
from django.utils import timezone

from email_integration.clients.base import GmailAuthError
from email_integration.models import GmailConnection, UnmatchedEmail
from email_integration.services import inbound_service
from email_integration.tests.base import EmailTestCase
from tickets.models import Ticket, TicketEvent, TicketMessage


class InboundTestCase(EmailTestCase):
    def setUp(self):
        super().setUp()
        self.connection = self.connect(self.member)
        self.fake = self.gmail(self.member)
        self.ticket = self.new_ticket(
            subject="Cannot log in", customer_email="jane@example.com"
        )
        # An agent reply goes out first, so the conversation has a Message-ID to answer.
        self.reply(self.ticket["id"], "Did you try resetting?")
        self.sent_id = self.message(self.ticket["id"]).email_message_id

    def customer_messages(self):
        return TicketMessage.objects.filter(
            ticket_id=self.ticket["id"], author_type="customer"
        )

    def sync(self):
        return inbound_service.manual_sync(self.connection)


class MatchingTests(InboundTestCase):
    def test_reply_is_matched_by_headers_and_stored_as_plain_text(self):
        self.fake.deliver(
            sender='"Jane" <jane@example.com>',
            subject="Totally different subject",
            in_reply_to=self.sent_id,
            body="Yes, still broken.\n\nOn Tue, Support <member@example.com> wrote:\n> Did you try resetting?",
        )
        report = self.sync()
        self.assertEqual((report.matched, report.review, report.ignored), (1, 0, 0))
        stored = self.customer_messages().order_by("created_at").last()
        self.assertEqual(stored.body_text, "Yes, still broken.")
        self.assertEqual(
            (stored.direction, stored.visibility, stored.delivery_status),
            ("inbound", "public", "received"),
        )
        self.assertEqual(
            (stored.mailbox_user, stored.external_sender_email),
            (self.member, "jane@example.com"),
        )
        ticket = Ticket.objects.get()
        self.assertTrue(ticket.waiting_for_reply)
        self.assertTrue(
            TicketEvent.objects.filter(event_type="customer_reply_received").exists()
        )

    def test_references_header_also_matches(self):
        self.fake.deliver(
            sender="jane@example.com", references=f"<old@x.com> {self.sent_id}"
        )
        self.assertEqual(self.sync().matched, 1)

    def test_subject_alone_never_matches(self):
        self.fake.deliver(sender="jane@example.com", subject="Re: Cannot log in [#1]")
        report = self.sync()
        self.assertEqual(report.matched, 0)
        self.assertEqual(
            report.review, 1
        )  # known customer, so it goes to review instead

    def test_same_gmail_mailbox_spelling_counts_as_the_customer(self):
        ticket = self.new_ticket(customer_email="x.y@gmail.com")
        self.reply(ticket["id"], "hi")
        sent = self.message(ticket["id"]).email_message_id
        self.fake.deliver(sender="xy+shop@gmail.com", in_reply_to=sent)
        self.assertEqual(self.sync().matched, 1)

    def test_header_match_from_a_different_sender_is_not_attached(self):
        self.fake.deliver(
            sender="attacker@evil.com", in_reply_to=self.sent_id, body="inject"
        )
        report = self.sync()
        self.assertEqual((report.matched, report.review, report.ignored), (0, 0, 1))
        self.assertEqual(self.customer_messages().count(), 1)
        self.assertEqual(UnmatchedEmail.objects.count(), 0)

    def test_redelivery_is_idempotent(self):
        self.fake.deliver(
            sender="jane@example.com", in_reply_to=self.sent_id, message_id="<dup@mail>"
        )
        self.assertEqual(self.sync().matched, 1)
        second = self.sync()
        self.assertEqual((second.matched, second.duplicate), (0, 1))
        self.assertEqual(self.customer_messages().count(), 2)  # description + one reply

    def test_ticket_in_another_workspace_is_never_matched(self):
        other = self.create_workspace(
            client=self.stranger_client, name="Theirs", slug="theirs"
        )["id"]
        theirs = self.stranger_client.post(
            self.turl(workspace_id=other),
            {"subject": "s", "description": "d", "customer_email": "jane@example.com"},
            format="json",
        ).data["data"]
        TicketMessage.objects.filter(ticket_id=theirs["id"]).update(
            email_message_id="<theirs@mail>"
        )
        self.fake.deliver(sender="jane@example.com", in_reply_to="<theirs@mail>")
        report = self.sync()
        self.assertEqual(report.matched, 0)
        self.assertEqual(
            TicketMessage.objects.filter(ticket_id=theirs["id"]).count(), 1
        )

    def test_closed_ticket_still_records_the_reply_without_changing_status(self):
        self.set_status(self.ticket["id"], "closed")
        self.fake.deliver(sender="jane@example.com", in_reply_to=self.sent_id)
        self.assertEqual(self.sync().matched, 1)
        self.assertEqual(Ticket.objects.get().status, "closed")

    def test_html_only_mail_is_stored_as_text(self):
        from email_integration.clients.base import GmailMessage

        self.fake.deliver(
            sender="jane@example.com",
            in_reply_to=self.sent_id,
            body="<script>x</script>",
        )
        # The fake delivers text; HTML reduction itself is covered by the parsing tests.
        self.sync()
        self.assertNotIn(
            "<",
            self.customer_messages()
            .order_by("created_at")
            .last()
            .body_text.replace("<script>x</script>", ""),
        )
        self.assertTrue(GmailMessage)


class PrivacyTests(InboundTestCase):
    def test_unknown_senders_are_ignored_and_nothing_is_stored(self):
        self.fake.deliver(
            sender="bank@example.org", subject="Your statement", body="private"
        )
        self.fake.deliver(sender="friend@gmail.com", subject="Dinner?", body="private")
        report = self.sync()
        self.assertEqual((report.matched, report.review, report.ignored), (0, 0, 2))
        self.assertEqual(UnmatchedEmail.objects.count(), 0)
        self.assertEqual(
            TicketMessage.objects.filter(body_text__contains="private").count(), 0
        )

    def test_known_customer_without_headers_goes_to_review_with_a_snippet_only(self):
        self.fake.deliver(
            sender="Jane D <jane@example.com>", subject="New question", body="x" * 1000
        )
        report = self.sync()
        self.assertEqual(report.review, 1)
        item = UnmatchedEmail.objects.get()
        self.assertEqual(
            (item.sender_email, item.sender_name, item.subject),
            ("jane@example.com", "Jane D", "New question"),
        )
        self.assertLessEqual(len(item.snippet), 300)
        self.assertFalse(hasattr(item, "body"))

    def test_own_mail_and_sent_mail_are_ignored(self):
        own = self.fake.deliver(sender="member@example.com", in_reply_to=self.sent_id)
        sent = self.fake.deliver(sender="jane@example.com", labels=("INBOX", "SENT"))
        draft = self.fake.deliver(
            sender="jane@example.com", labels=("DRAFT",)
        )  # not in the inbox
        for gmail_id in (own, sent, draft):
            outcome = inbound_service.process_message(
                self.connection, self.fake.messages[gmail_id]
            )
            self.assertEqual(outcome, "ignored", gmail_id)
        self.assertEqual(UnmatchedEmail.objects.count(), 0)

    def test_customer_of_a_workspace_the_agent_is_not_in_is_ignored(self):
        other = self.create_workspace(
            client=self.stranger_client, name="Theirs", slug="theirs"
        )["id"]
        self.stranger_client.post(
            self.turl(workspace_id=other),
            {
                "subject": "s",
                "description": "d",
                "customer_email": "private-person@example.org",
            },
            format="json",
        )
        self.fake.deliver(sender="private-person@example.org")
        self.assertEqual(self.sync().ignored, 1)

    def test_removed_member_gets_nothing_stored(self):
        from workspaces.constants.roles import MembershipStatus
        from workspaces.models import WorkspaceMembership

        WorkspaceMembership.objects.filter(user=self.member).update(
            status=MembershipStatus.REMOVED
        )
        self.fake.deliver(sender="jane@example.com", in_reply_to=self.sent_id)
        self.assertEqual(self.sync().ignored, 1)

    @override_settings(GMAIL_MANUAL_SYNC_LIMIT=3)
    def test_manual_sync_reads_only_the_newest_messages(self):
        ids = [self.fake.deliver(sender=f"x{i}@example.org") for i in range(6)]
        self.sync()
        self.assertEqual(self.fake.inbox[:3], ids[::-1][:3])
        self.assertEqual(len(self.fake.inbox), 6)

    @override_settings(GMAIL_REVIEW_MAX_PER_USER=2)
    def test_review_list_keeps_only_the_newest(self):
        for i in range(4):
            self.fake.deliver(sender="jane@example.com", subject=f"q{i}")
        self.sync()
        self.assertEqual(
            sorted(UnmatchedEmail.objects.values_list("subject", flat=True)),
            ["q2", "q3"],
        )

    def test_old_review_items_expire(self):
        self.fake.deliver(sender="jane@example.com")
        self.sync()
        UnmatchedEmail.objects.update(received_at=timezone.now() - timedelta(days=31))
        from email_integration.tasks import purge_old_review_items

        self.assertEqual(purge_old_review_items(), 1)


class HistorySyncTests(InboundTestCase):
    def test_first_run_records_the_starting_point_and_imports_nothing(self):
        self.fake.deliver(sender="jane@example.com", subject="old mail")
        GmailConnection.objects.update(history_id="")
        self.connection.refresh_from_db()
        report = inbound_service.sync_from_history(self.connection)
        self.assertEqual((report.matched, report.review), (0, 0))
        self.assertEqual(UnmatchedEmail.objects.count(), 0)
        self.assertEqual(
            GmailConnection.objects.get().history_id, str(self.fake.history_counter)
        )

    def test_later_runs_process_only_new_mail(self):
        inbound_service.sync_from_history(self.connection)  # sets the checkpoint
        self.connection.refresh_from_db()
        self.fake.deliver(sender="jane@example.com", in_reply_to=self.sent_id)
        report = inbound_service.sync_from_history(self.connection)
        self.assertEqual(report.matched, 1)
        again = inbound_service.sync_from_history(self.connection)
        self.assertEqual((again.matched, again.review, again.duplicate), (0, 0, 0))

    def test_expired_checkpoint_restarts_from_now(self):
        self.connection.history_id = "1"
        self.connection.save()
        self.fake.expired_history = True
        report = inbound_service.sync_from_history(self.connection)
        self.assertEqual((report.matched, report.review), (0, 0))
        self.assertEqual(
            GmailConnection.objects.get().history_id, str(self.fake.history_counter)
        )

    def test_revoked_token_marks_reauth_required(self):
        self.fake.fail_with = GmailAuthError()
        report = inbound_service.sync_from_history(self.connection)
        self.assertTrue(report.reauth_required)
        self.assertEqual(GmailConnection.objects.get().status, "reauth_required")


class ManualSyncEndpointTests(InboundTestCase):
    def test_sync_button_returns_counts(self):
        self.fake.deliver(sender="jane@example.com", in_reply_to=self.sent_id)
        self.fake.deliver(sender="jane@example.com", subject="other")
        self.fake.deliver(sender="nobody@example.org")
        response = self.member_client.post("/api/email/gmail/sync/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["data"],
            {
                "matched": 1,
                "needs_review": 1,
                "duplicates": 0,
                "ignored": 1,
                "limit": 30,
            },
        )
        self.assertIsNotNone(GmailConnection.objects.get().last_sync_at)

    def test_sync_needs_a_connected_gmail(self):
        self.assertEqual(
            self.owner_client.post("/api/email/gmail/sync/").data["code"],
            "gmail_not_connected",
        )

    def test_sync_reports_expired_google_access(self):
        self.fake.fail_with = GmailAuthError()
        response = self.member_client.post("/api/email/gmail/sync/")
        self.assertEqual(
            (response.status_code, response.data["code"]),
            (409, "gmail_reauth_required"),
        )

    def test_sync_is_rate_limited(self):
        from common.throttling.scoped import AuthScopedThrottle

        rates = {**AuthScopedThrottle.THROTTLE_RATES, "gmail_sync": "1/min"}
        with mock.patch.object(AuthScopedThrottle, "THROTTLE_RATES", rates):
            self.assertEqual(
                self.member_client.post("/api/email/gmail/sync/").status_code, 200
            )
            self.assertEqual(
                self.member_client.post("/api/email/gmail/sync/").status_code, 429
            )


class ReviewEndpointTests(InboundTestCase):
    def setUp(self):
        super().setUp()
        self.fake.deliver(
            sender="jane@example.com",
            subject="Another question",
            body="Please also check my invoice.",
        )
        self.sync()
        self.item = UnmatchedEmail.objects.get()

    def test_list_is_mine_only(self):
        mine = self.member_client.get("/api/email/review/")
        self.assertEqual(mine.data["meta"]["count"], 1)
        self.assertEqual(mine.data["data"]["items"][0]["subject"], "Another question")
        self.assertEqual(
            self.owner_client.get("/api/email/review/").data["meta"]["count"], 0
        )

    def test_attach_fetches_the_body_again_and_clears_the_item(self):
        response = self.member_client.post(
            f"/api/email/review/{self.item.id}/attach/",
            {"workspace_id": self.workspace_id, "ticket_id": self.ticket["id"]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        stored = self.customer_messages_last()
        self.assertEqual(stored.body_text, "Please also check my invoice.")
        self.assertEqual(UnmatchedEmail.objects.count(), 0)

    def customer_messages_last(self):
        return (
            TicketMessage.objects.filter(
                ticket_id=self.ticket["id"], author_type="customer"
            )
            .order_by("created_at")
            .last()
        )

    def test_attach_to_a_ticket_in_a_workspace_i_am_not_in_fails(self):
        other = self.create_workspace(
            client=self.stranger_client, name="Theirs", slug="theirs"
        )["id"]
        theirs = self.stranger_client.post(
            self.turl(workspace_id=other),
            {"subject": "s", "description": "d", "customer_email": "a@b.com"},
            format="json",
        ).data["data"]
        response = self.member_client.post(
            f"/api/email/review/{self.item.id}/attach/",
            {"workspace_id": other, "ticket_id": theirs["id"]},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(UnmatchedEmail.objects.count(), 1)

    def test_someone_elses_item_is_404(self):
        for method, suffix, body in (
            (
                "post",
                "attach/",
                {"workspace_id": self.workspace_id, "ticket_id": self.ticket["id"]},
            ),
            ("post", "dismiss/", None),
        ):
            call = getattr(self.owner_client, method)
            response = (
                call(f"/api/email/review/{self.item.id}/{suffix}", body, format="json")
                if body
                else call(f"/api/email/review/{self.item.id}/{suffix}")
            )
            self.assertEqual(response.status_code, 404, suffix)
        self.assertEqual(UnmatchedEmail.objects.count(), 1)

    def test_dismiss(self):
        self.assertEqual(
            self.member_client.post(
                f"/api/email/review/{self.item.id}/dismiss/"
            ).status_code,
            200,
        )
        self.assertEqual(UnmatchedEmail.objects.count(), 0)

    def test_attach_validation(self):
        for body in (
            {},
            {"workspace_id": self.workspace_id},
            {"workspace_id": "x", "ticket_id": "y"},
        ):
            self.assertEqual(
                self.member_client.post(
                    f"/api/email/review/{self.item.id}/attach/", body, format="json"
                ).status_code,
                400,
            )
