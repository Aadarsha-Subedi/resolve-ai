from datetime import UTC, datetime, timedelta

from tickets.models import Ticket
from tickets.tests.base import TicketTestCase


class DashboardTestCase(TicketTestCase):
    """A workspace with an owner and a member (from TicketTestCase)."""

    def setUp(self):
        super().setUp()
        self.durl = f"/api/workspaces/{self.workspace_id}/dashboard/"

    def dash(self, query="", client=None, workspace_id=None):
        url = (
            self.durl
            if workspace_id is None
            else self.durl.replace(str(self.workspace_id), str(workspace_id))
        )
        return (client or self.member_client).get(url + query)

    def data(self, query="", client=None) -> dict:
        response = self.dash(query, client)
        assert response.status_code == 200, response.content
        return response.data["data"]

    def make(self, **fields) -> Ticket:
        """Create a ticket through the API, then set raw fields (timestamps, status)."""
        created = self.new_ticket(
            **{k: fields.pop(k) for k in ("priority", "subject") if k in fields}
        )
        ticket = Ticket.objects.get(pk=created["id"])
        if fields:
            Ticket.objects.filter(pk=ticket.pk).update(**fields)
            ticket.refresh_from_db()
        return ticket

    @staticmethod
    def at(day: str, hour: int = 12, minute: int = 0) -> datetime:
        year, month, date = map(int, day.split("-"))
        return datetime(year, month, date, hour, minute, tzinfo=UTC)

    @staticmethod
    def ago(**delta) -> datetime:
        return datetime.now(UTC) - timedelta(**delta)
