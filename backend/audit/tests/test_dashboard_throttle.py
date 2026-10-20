from audit.tests.dashboard_base import DashboardTestCase


class DashboardThrottleTests(DashboardTestCase):
    def test_30_requests_a_minute_per_user(self):
        for _ in range(30):
            self.assertEqual(self.dash(client=self.member_client).status_code, 200)
        self.assertEqual(self.dash(client=self.member_client).status_code, 429)
        # Another user is unaffected.
        self.assertEqual(self.dash(client=self.owner_client).status_code, 200)
