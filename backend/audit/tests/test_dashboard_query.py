from audit.tests.dashboard_base import DashboardTestCase


class QueryValidationTests(DashboardTestCase):
    def assert_400(self, query):
        response = self.dash(query)
        self.assertEqual(response.status_code, 400, response.content)

    def test_unknown_parameters_are_rejected(self):
        self.assert_400("?bogus=1")
        self.assert_400("?limit=5")

    def test_period_choices(self):
        for period in ("7d", "30d", "90d"):
            self.assertEqual(self.dash(f"?period={period}").status_code, 200)
        self.assert_400("?period=14d")

    def test_custom_range_rules(self):
        self.assert_400("?from=2026-01-01")  # needs both
        self.assert_400("?to=2026-01-01")
        self.assert_400("?from=2026-02-01&to=2026-01-01")  # backwards
        self.assert_400("?period=7d&from=2026-01-01&to=2026-01-05")  # not both
        self.assert_400("?from=nope&to=2026-01-05")
        self.assertEqual(self.dash("?from=2026-01-01&to=2026-01-01").status_code, 200)

    def test_custom_range_max_366_days(self):
        # 2025-01-01 .. 2026-01-01 is 366 days inclusive.
        self.assertEqual(self.dash("?from=2025-01-01&to=2026-01-01").status_code, 200)
        self.assert_400("?from=2025-01-01&to=2026-01-02")

    def test_legacy_timezone_aliases_are_canonicalised(self):
        for legacy, canonical in (
            ("Asia/Katmandu", "Asia/Kathmandu"),
            ("Asia/Calcutta", "Asia/Kolkata"),
            ("US/Eastern", "America/New_York"),
        ):
            period = self.data(f"?tz={legacy}")["period"]
            self.assertEqual(period["tz"], canonical)

    def test_valid_timezone_is_echoed(self):
        self.assertEqual(
            self.data("?tz=Europe/Berlin")["period"]["tz"], "Europe/Berlin"
        )

    def test_unknown_timezone_is_a_400_with_the_stable_code(self):
        response = self.dash("?tz=Asia/Nowhere")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")

    def test_timezone(self):
        self.assertEqual(self.dash("?tz=Asia/Kathmandu").status_code, 200)
        self.assert_400("?tz=Mars/Base")
        self.assert_400("?tz=../etc/passwd")
        self.assert_400("?tz=")

    def test_include(self):
        self.assert_400("?include=summary,nope")
        self.assert_400("?include=")
        self.assertEqual(self.dash("?include=summary , volume").status_code, 200)

    def test_include_returns_only_those_sections(self):
        data = self.data("?include=waiting,summary")
        self.assertEqual(set(data), {"generated_at", "period", "summary", "waiting"})
        only = self.data("?include=activity")
        self.assertEqual(set(only), {"generated_at", "period", "activity"})

    def test_default_returns_every_section(self):
        self.assertEqual(
            set(self.data()),
            {
                "generated_at",
                "period",
                "summary",
                "volume",
                "recent_tickets",
                "waiting",
                "activity",
            },
        )

    def test_limits_are_bounded(self):
        for name in ("recent_limit", "waiting_limit", "activity_limit"):
            self.assert_400(f"?{name}=0")
            self.assert_400(f"?{name}=51")
            self.assert_400(f"?{name}=abc")
            self.assertEqual(self.dash(f"?{name}=50").status_code, 200)

    def test_default_limits(self):
        for _ in range(12):
            self.make()
        data = self.data()
        self.assertEqual(len(data["recent_tickets"]["items"]), 5)
        self.assertEqual(len(data["waiting"]["items"]), 5)
        self.assertEqual(len(data["activity"]["items"]), 10)

    def test_error_uses_the_envelope(self):
        body = self.dash("?bogus=1").data
        self.assertFalse(body["success"])
        self.assertEqual(body["status_code"], 400)


class PeriodTests(DashboardTestCase):
    def test_default_is_30_days_ending_today_with_a_previous_period(self):
        period = self.data()["period"]
        self.assertEqual(period["key"], "30d")
        self.assertEqual((period["days"], period["tz"]), (30, "UTC"))
        from datetime import date, timedelta

        start, end = (
            date.fromisoformat(period["from"]),
            date.fromisoformat(period["to"]),
        )
        self.assertEqual((end - start).days, 29)
        prev = period["previous"]
        self.assertEqual(date.fromisoformat(prev["to"]), start - timedelta(days=1))
        self.assertEqual(
            (date.fromisoformat(prev["to"]) - date.fromisoformat(prev["from"])).days, 29
        )

    def test_custom_period_and_previous_have_the_same_length(self):
        period = self.data("?from=2026-03-10&to=2026-03-16")["period"]
        self.assertEqual(
            period,
            {
                "key": "custom",
                "from": "2026-03-10",
                "to": "2026-03-16",
                "days": 7,
                "tz": "UTC",
                "previous": {"from": "2026-03-03", "to": "2026-03-09"},
            },
        )

    def test_custom_period_counts_current_and_previous(self):
        self.make(created_at=self.at("2026-03-10", 0, 0))  # first instant of the range
        self.make(created_at=self.at("2026-03-16", 23, 59))  # last minute of the range
        self.make(created_at=self.at("2026-03-17", 0, 0))  # just after
        self.make(created_at=self.at("2026-03-09", 23, 59))  # previous
        self.make(created_at=self.at("2026-03-03", 0, 0))  # previous, first instant
        self.make(created_at=self.at("2026-03-02", 23, 59))  # before previous
        s = self.data("?from=2026-03-10&to=2026-03-16")["summary"]
        self.assertEqual(s["created"], {"current": 2, "previous": 2})
