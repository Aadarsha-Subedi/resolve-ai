from unittest import mock

from django.core.cache import cache

from common.throttling.scoped import IPScopedThrottle
from tickets.models import Ticket, TicketEvent, TicketMessage
from tickets.tests.base import TicketTestCase


class PortalInfoTests(TicketTestCase):
    def test_public_info_has_only_public_fields(self):
        data = self.anon.get("/api/portal/acme/").data["data"]
        self.assertEqual(set(data), {"name", "slug", "logo_url"})
        self.assertEqual((data["name"], data["slug"]), ("Acme Support", "acme"))

    def test_unknown_disabled_and_deleted_all_look_the_same(self):
        self.owner_client.patch(
            f"/api/workspaces/{self.workspace_id}/",
            {"portal_enabled": False},
            format="json",
        )
        disabled = self.anon.get("/api/portal/acme/")
        unknown = self.anon.get("/api/portal/nothing-here/")
        self.assertEqual((disabled.status_code, unknown.status_code), (404, 404))
        self.assertEqual(disabled.data["message"], unknown.data["message"])
        self.owner_client.patch(
            f"/api/workspaces/{self.workspace_id}/",
            {"portal_enabled": True},
            format="json",
        )
        self.assertEqual(self.anon.get("/api/portal/acme/").status_code, 200)
        self.owner_client.delete(f"/api/workspaces/{self.workspace_id}/")
        self.assertEqual(self.anon.get("/api/portal/acme/").status_code, 404)


class PortalSubmitTests(TicketTestCase):
    def test_anonymous_customer_creates_a_ticket(self):
        response = self.portal({"customer_name": "Cara", "category": "billing"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"], {"number": 1})
        self.assertIn("#1", response.data["message"])
        ticket = Ticket.objects.get()
        self.assertEqual(
            (
                ticket.created_via,
                ticket.status,
                ticket.priority,
                ticket.category,
                ticket.customer_name,
                ticket.created_by,
            ),
            ("portal", "open", "medium", "billing", "Cara", None),
        )
        self.assertTrue(ticket.confirmation_pending)
        self.assertEqual(TicketMessage.objects.get().author_type, "customer")
        self.assertEqual(TicketEvent.objects.get().event_type, "created")

    def test_response_leaks_nothing_internal(self):
        response = self.portal()
        self.assertEqual(set(response.data["data"]), {"number"})
        body = str(response.data)
        for secret in (
            self.workspace_id,
            "cust@example.com",
            "priority",
            "status', 'open",
        ):
            self.assertNotIn(secret, body)

    def test_works_without_csrf_cookie_or_session(self):
        from rest_framework.test import APIClient

        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(self.portal(client=client).status_code, 201)

    def test_customers_cannot_set_priority_or_status_or_unknown_fields(self):
        for extra in (
            {"priority": "urgent"},
            {"status": "closed"},
            {"number": 99},
            {"workspace": "x"},
        ):
            self.assertEqual(self.portal(extra).status_code, 400, extra)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_validation(self):
        for body in (
            {"subject": ""},
            {"description": ""},
            {"customer_email": "nope"},
            {"subject": "x" * 201},
            {"description": "x" * 20001},
            {"category": "sales"},
        ):
            self.assertEqual(self.portal(body).status_code, 400, body)
        missing = self.anon.post(
            "/api/portal/acme/tickets/", {"subject": "s"}, format="json"
        )
        self.assertEqual(missing.status_code, 400)

    def test_disabled_or_unknown_portal_rejects_submissions(self):
        self.assertEqual(self.portal(slug="nope").status_code, 404)
        self.owner_client.patch(
            f"/api/workspaces/{self.workspace_id}/",
            {"portal_enabled": False},
            format="json",
        )
        self.assertEqual(self.portal().status_code, 404)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_honeypot_looks_like_success_but_creates_nothing(self):
        response = self.portal({"website": "http://spam.example"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.data["data"]), {"number"})
        self.assertEqual(
            (Ticket.objects.count(), TicketMessage.objects.count()), (0, 0)
        )
        self.assertEqual(
            self.portal({"website": ""}).status_code, 201
        )  # an empty honeypot is normal
        self.assertEqual(Ticket.objects.count(), 1)

    def test_per_email_limit_per_workspace(self):
        for _ in range(5):
            self.assertEqual(self.portal().status_code, 201)
        blocked = self.portal()
        self.assertEqual(
            (blocked.status_code, blocked.data["code"]),
            (429, "portal_email_rate_limited"),
        )
        self.assertEqual(
            self.portal({"customer_email": "CUST@example.com"}).status_code, 429
        )  # same mailbox
        self.assertEqual(
            self.portal({"customer_email": "other@example.com"}).status_code, 201
        )
        self.assertEqual(Ticket.objects.count(), 6)

    def test_email_limit_is_per_workspace(self):
        other = self.create_workspace(
            client=self.stranger_client, name="Other", slug="other"
        )["id"]
        for _ in range(5):
            self.portal()
        self.assertEqual(self.portal().status_code, 429)
        self.assertEqual(self.portal(slug="other").status_code, 201)
        self.assertEqual(Ticket.objects.filter(workspace_id=other).count(), 1)

    def test_per_ip_throttle(self):
        rates = {**IPScopedThrottle.THROTTLE_RATES, "portal_ticket": "2/hour"}
        cache.clear()
        with mock.patch.object(IPScopedThrottle, "THROTTLE_RATES", rates):
            codes = [
                self.portal({"customer_email": f"u{i}@example.com"}).status_code
                for i in range(3)
            ]
        self.assertEqual(codes, [201, 201, 429])

    def test_portal_tickets_are_numbered_with_agent_tickets(self):
        self.new_ticket()
        self.assertEqual(self.portal().data["data"]["number"], 2)

    def test_agents_see_portal_tickets_and_the_customer_message(self):
        self.portal({"subject": "Where is my order?"})
        listed = self.member_client.get(self.turl()).data["data"]["items"]
        self.assertEqual(
            (
                listed[0]["subject"],
                listed[0]["created_via"],
                listed[0]["waiting_for_reply"],
            ),
            ("Where is my order?", "portal", True),
        )
        messages = self.member_client.get(
            self.turl(f"{listed[0]['id']}/messages/")
        ).data["data"]["items"]
        self.assertEqual([m["author_type"] for m in messages], ["customer"])

    def test_no_customer_endpoint_exposes_tickets(self):
        self.portal()
        ticket = Ticket.objects.get()
        for url in (
            f"/api/portal/acme/tickets/{ticket.id}/",
            f"/api/portal/acme/tickets/{ticket.number}/",
            f"/api/workspaces/{self.workspace_id}/tickets/{ticket.id}/",
        ):
            self.assertIn(self.anon.get(url).status_code, (401, 404), url)
