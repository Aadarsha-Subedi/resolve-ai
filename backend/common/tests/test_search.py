from unittest import skipIf, skipUnless

from django.db import connection
from django.test import SimpleTestCase, TestCase

from common.exception.domain import ValidationException
from common.search import constants
from common.search.query import (
    normalize_query,
    order_by_relevance,
    search,
    with_headline,
)
from workspaces.models import Workspace

POSTGRES = connection.vendor == "postgresql"


class NormalizeQueryTests(SimpleTestCase):
    def test_empty_becomes_none(self):
        for value in (None, "", "   "):
            self.assertIsNone(normalize_query(value))

    def test_whitespace_is_collapsed(self):
        self.assertEqual(normalize_query("  late \t delivery  "), "late delivery")

    def test_length_limits(self):
        for bad in ("a", "x" * (constants.QUERY_MAX_LENGTH + 1)):
            with self.assertRaises(ValidationException) as ctx:
                normalize_query(bad)
            self.assertEqual(
                ctx.exception.error_code, constants.ERROR_INVALID_SEARCH_QUERY
            )
        self.assertEqual(normalize_query("ab"), "ab")


class SearchTestCase(TestCase):
    """Uses Workspace.name as a stand-in text column until real vectors exist."""

    def make(self, *names):
        for i, name in enumerate(names):
            Workspace.objects.create(name=name, slug=f"ws-{i}-{name[:4].lower()}")

    def queryset(self):
        if POSTGRES:
            from django.contrib.postgres.search import SearchVector

            return Workspace.objects.annotate(
                sv=SearchVector("name", weight="A", config="english")
            )
        return Workspace.objects.all()

    def run_search(self, q, **extra):
        return search(
            self.queryset(),
            q,
            config="english",
            vector_field="sv",
            fallback_fields=("name",),
            **extra,
        )


@skipIf(POSTGRES, "fallback is only used off Postgres")
class FallbackSearchTests(SearchTestCase):
    def test_contains_match_case_insensitive(self):
        self.make("Acme Support", "Globex")
        names = list(self.run_search("ACME").values_list("name", flat=True))
        self.assertEqual(names, ["Acme Support"])

    def test_rank_is_constant_and_headline_empty(self):
        self.make("Acme Support")
        row = with_headline(
            self.run_search("acme"), text_field="name", q="acme", config="english"
        ).get()
        self.assertEqual((row.rank, row.headline), (0.0, ""))

    def test_relevance_ordering_is_stable(self):
        self.make("Acme One", "Acme Two")
        qs = order_by_relevance(self.run_search("acme"), tiebreak=("name",))
        self.assertEqual(
            list(qs.values_list("name", flat=True)), ["Acme One", "Acme Two"]
        )


@skipUnless(POSTGRES, "needs Postgres full-text search")
class PostgresSearchTests(SearchTestCase):
    def names(self, qs):
        return list(qs.values_list("name", flat=True))

    def test_stemming_matches_word_forms(self):
        self.make("Refund policy", "Shipping times")
        self.assertEqual(self.names(self.run_search("refunds")), ["Refund policy"])

    def test_websearch_phrase_and_exclusion(self):
        self.make("late delivery issue", "delivery late", "late delivery spam")
        phrase = self.names(self.run_search('"late delivery"').order_by("name"))
        self.assertEqual(phrase, ["late delivery issue", "late delivery spam"])
        excluded = self.names(self.run_search("delivery -spam").order_by("name"))
        self.assertEqual(excluded, ["delivery late", "late delivery issue"])

    def test_user_input_never_raises(self):
        self.make("Acme")
        for q in ('"unclosed', "a & | ! (", "'; DROP TABLE x; --", ":*"):
            list(self.run_search(q))

    def test_rank_is_between_zero_and_one_and_orders_results(self):
        self.make("refund", "refund refund refund and many other unrelated words here")
        qs = order_by_relevance(self.run_search("refund"), tiebreak=("name",))
        ranks = [row.rank for row in qs]
        self.assertTrue(all(0 < r < 1 for r in ranks), ranks)
        self.assertEqual(ranks, sorted(ranks, reverse=True))

    def test_headline_uses_sentinel_markers_not_html(self):
        self.make("Our <b>refund</b> policy")
        row = with_headline(
            self.run_search("refund"), text_field="name", q="refund", config="english"
        ).get()
        marked = f"{constants.HIGHLIGHT_START}refund{constants.HIGHLIGHT_STOP}"
        self.assertIn(marked, row.headline)

    def test_query_uses_the_given_config(self):
        self.make("Los reembolsos")
        qs = Workspace.objects.all()
        from django.contrib.postgres.search import SearchVector

        qs = qs.annotate(sv=SearchVector("name", config="spanish"))
        found = search(qs, "reembolso", config="spanish", vector_field="sv")
        self.assertEqual(found.count(), 1)
