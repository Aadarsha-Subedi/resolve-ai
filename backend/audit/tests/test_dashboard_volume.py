from audit.tests.dashboard_base import DashboardTestCase
from tickets.models import Ticket


class VolumeTests(DashboardTestCase):
    def volume(self, query):
        return self.data(query + "&include=volume")["volume"]

    def test_daily_buckets_are_zero_filled(self):
        self.make(created_at=self.at("2026-03-11"))
        self.make(created_at=self.at("2026-03-11", 18))
        self.make(created_at=self.at("2026-03-13"))
        volume = self.volume("?from=2026-03-10&to=2026-03-14")
        self.assertEqual(volume["granularity"], "day")
        self.assertEqual(
            [
                (b["start"], b["end"], b["created"], b["resolved"])
                for b in volume["buckets"]
            ],
            [
                ("2026-03-10", "2026-03-10", 0, 0),
                ("2026-03-11", "2026-03-11", 2, 0),
                ("2026-03-12", "2026-03-12", 0, 0),
                ("2026-03-13", "2026-03-13", 1, 0),
                ("2026-03-14", "2026-03-14", 0, 0),
            ],
        )

    def test_presets_up_to_a_month_are_daily_longer_are_weekly(self):
        self.assertEqual(len(self.volume("?period=7d")["buckets"]), 7)
        month = self.volume("?period=30d")
        self.assertEqual((month["granularity"], len(month["buckets"])), ("day", 30))
        quarter = self.volume("?period=90d")
        self.assertEqual(quarter["granularity"], "week")
        self.assertEqual(len(quarter["buckets"]), 13)  # 12 full weeks + 6 days

    def test_weekly_buckets_cover_the_range_without_gaps_and_sum(self):
        for day in ("2026-01-01", "2026-01-07", "2026-01-08", "2026-02-19"):
            self.make(created_at=self.at(day))
        volume = self.volume("?from=2026-01-01&to=2026-02-19")
        self.assertEqual(volume["granularity"], "week")
        buckets = volume["buckets"]
        self.assertEqual(buckets[0]["start"], "2026-01-01")
        self.assertEqual(buckets[0]["end"], "2026-01-07")
        self.assertEqual(buckets[1]["start"], "2026-01-08")
        self.assertEqual(buckets[-1]["end"], "2026-02-19")  # last bucket is short
        self.assertEqual([b["created"] for b in buckets], [2, 1, 0, 0, 0, 0, 0, 1])
        self.assertEqual(sum(b["created"] for b in buckets), 4)

    def test_resolved_series_follows_resolved_at(self):
        t = self.make(created_at=self.at("2026-03-10"))
        self.set_status(t.id, "resolved")
        Ticket.objects.filter(pk=t.pk).update(resolved_at=self.at("2026-03-12"))
        buckets = self.volume("?from=2026-03-10&to=2026-03-13")["buckets"]
        self.assertEqual([b["created"] for b in buckets], [1, 0, 0, 0])
        self.assertEqual([b["resolved"] for b in buckets], [0, 0, 1, 0])

    def test_time_zone_moves_tickets_across_midnight(self):
        # 23:30 UTC on Mar 11 is 05:15 on Mar 12 in Kathmandu (UTC+5:45).
        self.make(created_at=self.at("2026-03-11", 23, 30))
        utc = self.volume("?from=2026-03-10&to=2026-03-13")["buckets"]
        self.assertEqual([b["created"] for b in utc], [0, 1, 0, 0])
        local = self.volume("?from=2026-03-10&to=2026-03-13&tz=Asia/Kathmandu")[
            "buckets"
        ]
        self.assertEqual([b["created"] for b in local], [0, 0, 1, 0])

    def test_time_zone_moves_the_window_edges(self):
        self.make(created_at=self.at("2026-03-09", 20, 0))  # Mar 10 01:45 in Kathmandu
        self.assertEqual(
            self.data("?from=2026-03-10&to=2026-03-10")["summary"]["created"][
                "current"
            ],
            0,
        )
        self.assertEqual(
            self.data("?from=2026-03-10&to=2026-03-10&tz=Asia/Kathmandu")["summary"][
                "created"
            ]["current"],
            1,
        )

    def test_negative_offset_zone(self):
        # 02:00 UTC on Mar 11 is 22:00 on Mar 10 in New York (EDT, UTC-4).
        self.make(created_at=self.at("2026-03-11", 2, 0))
        buckets = self.volume("?from=2026-03-10&to=2026-03-11&tz=America/New_York")[
            "buckets"
        ]
        self.assertEqual([b["created"] for b in buckets], [1, 0])

    def test_bucket_totals_match_the_summary(self):
        for day in ("2026-03-10", "2026-03-10", "2026-03-15"):
            self.make(created_at=self.at(day))
        data = self.data("?from=2026-03-10&to=2026-03-16")
        self.assertEqual(
            sum(b["created"] for b in data["volume"]["buckets"]),
            data["summary"]["created"]["current"],
        )
