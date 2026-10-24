from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext

from audit.tests.dashboard_base import DashboardTestCase


class CacheTests(DashboardTestCase):
    def test_second_identical_call_is_served_from_the_cache(self):
        first = self.dash()
        second = self.dash()
        self.assertFalse(first.data["meta"]["cached"])
        self.assertTrue(second.data["meta"]["cached"])
        self.assertEqual(first.data["data"], second.data["data"])

    def test_cached_call_does_no_ticket_queries(self):
        self.dash()
        with CaptureQueriesContext(connection) as queries:
            self.dash()
        self.assertFalse([q for q in queries if "tickets_" in q["sql"]])

    def test_new_data_appears_after_the_cache_is_cleared(self):
        self.assertEqual(self.data()["summary"]["active"], 0)
        self.make()
        self.assertEqual(self.data()["summary"]["active"], 0)  # cached for 30 seconds
        cache.clear()
        self.assertEqual(self.data()["summary"]["active"], 1)

    def test_ttl_is_30_seconds(self):
        from audit.constants.dashboard import CACHE_TTL_SECONDS

        self.assertEqual(CACHE_TTL_SECONDS, 30)

    def test_parameter_order_does_not_change_the_entry(self):
        self.dash("?recent_limit=3&tz=UTC&include=summary,volume")
        again = self.dash("?include=volume,summary&tz=UTC&recent_limit=3")
        self.assertTrue(again.data["meta"]["cached"])

    def test_a_preset_and_the_same_dates_as_a_range_share_an_entry(self):
        first = self.data("?period=7d")["period"]
        again = self.dash(f"?from={first['from']}&to={first['to']}")
        self.assertTrue(again.data["meta"]["cached"])

    def test_different_queries_do_not_share_an_entry(self):
        self.dash("?period=7d")
        for query in (
            "?period=30d",
            "?period=7d&tz=Asia/Kathmandu",
            "?period=7d&include=summary",
            "?period=7d&recent_limit=6",
            "?period=7d&waiting_limit=6",
            "?period=7d&activity_limit=6",
        ):
            self.assertFalse(self.dash(query).data["meta"]["cached"], query)

    def test_workspaces_do_not_share_an_entry(self):
        other = self.create_workspace(
            client=self.stranger_client, name="Other", slug="other"
        )
        self.dash(client=self.owner_client)
        response = self.dash(workspace_id=other["id"], client=self.stranger_client)
        self.assertFalse(response.data["meta"]["cached"])
        self.assertEqual(response.data["data"]["summary"]["active"], 0)

    def test_members_of_one_workspace_share_the_entry(self):
        self.dash(client=self.owner_client)
        self.assertTrue(self.dash(client=self.member_client).data["meta"]["cached"])


class QueryCountTests(DashboardTestCase):
    def count(self, query=""):
        cache.clear()
        with CaptureQueriesContext(connection) as queries:
            response = self.dash(query)
        self.assertEqual(response.status_code, 200)
        return len(queries)

    def test_query_count_is_fixed_whatever_the_data_size(self):
        empty = self.count()
        for _ in range(12):
            t = self.make(last_customer_message_at=self.ago(hours=1))
            self.set_status(t.id, "in_progress")
        busy = self.count("?recent_limit=50&waiting_limit=50&activity_limit=50")
        self.assertEqual(empty, busy)
        # session (3) + membership (1) + summary, volume (2), lists (4), activity (1) + total
        self.assertLessEqual(busy, 13)

    def test_weekly_period_costs_the_same_as_daily(self):
        self.make()
        self.assertEqual(self.count("?period=7d"), self.count("?period=90d"))

    def test_include_only_runs_the_requested_queries(self):
        everything = self.count()
        self.assertLess(self.count("?include=summary"), everything)
