from unittest import skipUnless

from django.db import connection
from django.test import TestCase

from common.search.context import (
    CONTEXT_MAX_TERMS,
    context_query,
)

POSTGRES = connection.vendor == "postgresql"
MESSAGE = "I was charged twice for my annual plan and want my money back"


class ContextQueryTests(TestCase):
    def test_empty_and_wordless_text_gives_nothing(self):
        for text in (None, "", "   ", "!!! ??? ...", "the and of to a", "12 345"):
            result = context_query(text, "english")
            self.assertFalse(result, repr(text))
            self.assertEqual((result.terms, result.query), ([], None))

    def test_terms_are_capped_and_longest_first(self):
        text = " ".join(f"{'x' * n}{chr(97 + n)}" for n in range(3, 25))
        result = context_query(text, "english")
        self.assertEqual(len(result.terms), CONTEXT_MAX_TERMS)
        lengths = [len(t) for t in result.terms]
        self.assertEqual(lengths, sorted(lengths, reverse=True))

    def test_hostile_text_never_reaches_the_query_syntax(self):
        text = (
            "refund' | !secret & (a:*) <-> 'x' \\ ; DROP TABLE users -- " + "z" * 5000
        )
        result = context_query(text, "english")
        for term in result.terms:
            self.assertRegex(term, r"^[^\W_]+$")
        if POSTGRES and result.query is not None:
            self.assertNotIn("DROP TABLE", result.raw)

    def test_very_long_text_is_accepted(self):
        result = context_query("refund policy " * 100000, "english")
        self.assertTrue(result)


@skipUnless(POSTGRES, "needs Postgres text search")
class PostgresContextQueryTests(TestCase):
    def test_stems_and_drops_stop_words(self):
        result = context_query(MESSAGE, "english")
        self.assertEqual(
            set(result.terms),
            {"charg", "twice", "annual", "plan", "want", "money", "back"},
        )
        self.assertNotIn("the", result.terms)
        self.assertEqual(
            result.terms[0], "annual" if len("annual") > 5 else result.terms[0]
        )

    def test_inflections_collapse_to_one_term(self):
        result = context_query("refund refunds refunded refunding", "english")
        self.assertEqual(result.terms, ["refund"])

    def test_query_text_is_an_or_of_quoted_terms(self):
        result = context_query("refund annual", "english")
        self.assertEqual(result.raw, "'annual' | 'refund'")
        self.assertIsNotNone(result.query)

    def test_other_languages_use_their_own_stop_words(self):
        spanish = context_query("el reembolso de la factura", "spanish")
        self.assertNotIn("el", spanish.terms)
        self.assertNotIn("de", spanish.terms)
        self.assertTrue(spanish.terms)

    def test_query_runs_against_a_tsvector(self):
        from django.db import connection as conn

        result = context_query(MESSAGE, "english")
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT to_tsvector('english', %s) @@ to_tsquery('simple', %s)",
                [
                    "Our refund policy: money back within 14 days of your plan purchase",
                    result.raw,
                ],
            )
            self.assertTrue(cursor.fetchone()[0])
