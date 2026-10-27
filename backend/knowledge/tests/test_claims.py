import json

from django.test import SimpleTestCase

from knowledge.services import claim_service

PASSAGE = (
    "## Refunds\n\nYou can request a **refund** within 14 days of purchase for an "
    "annual plan.\nThe refund goes back to the original payment method.\n\n"
    "Monthly plans aren’t refunded after they renew."
)


def raw(*claims):
    return json.dumps(
        {"claims": [{"text": t, "cites": [{"n": n, "quote": q}]} for t, n, q in claims]}
    )


class VerifyClaimsTests(SimpleTestCase):
    def verify(self, *claims, passages=(PASSAGE,)):
        return claim_service.verify_claims(raw(*claims), list(passages))

    def test_an_exact_quote_is_kept_and_located(self):
        (claim,) = self.verify(("Refund in 14 days.", 1, "within 14 days of purchase"))
        cite = claim["cites"][0]
        self.assertEqual(cite["quote"], "within 14 days of purchase")
        self.assertTrue(cite["before"].endswith("request a **refund** "))
        self.assertTrue(cite["after"].startswith(" for an annual plan"))

    def test_case_spacing_markdown_and_quotes_are_ignored(self):
        for quote in (
            "WITHIN 14   DAYS of purchase",
            "request a refund within 14 days",
            "Monthly plans aren't refunded after they renew",
            "annual plan. The refund goes back",
        ):
            self.assertEqual(len(self.verify(("x", 1, quote))), 1, quote)

    def test_the_returned_quote_is_the_passages_own_text(self):
        (claim,) = self.verify(("x", 1, "REQUEST A REFUND WITHIN 14 DAYS"))
        self.assertEqual(
            claim["cites"][0]["quote"], "request a **refund** within 14 days"
        )

    def test_a_quote_not_in_the_passage_drops_the_claim(self):
        self.assertEqual(
            self.verify(("x", 1, "refunds within ninety days of purchase")), []
        )

    def test_a_quote_from_another_passage_does_not_count(self):
        passages = (PASSAGE, "Reset your password from the sign in page.")
        self.assertEqual(
            self.verify(("x", 2, "within 14 days of purchase"), passages=passages), []
        )

    def test_a_missing_passage_number_drops_the_claim(self):
        for n in (0, 2, -1, True, "1", None):
            self.assertEqual(self.verify(("x", n, "within 14 days of purchase")), [], n)

    def test_quote_length_limits(self):
        self.assertEqual(self.verify(("x", 1, "14 days")), [])  # too short
        long_passage = " ".join(f"word{i}" for i in range(60))
        quote = " ".join(f"word{i}" for i in range(41))
        self.assertEqual(self.verify(("x", 1, quote), passages=(long_passage,)), [])
        self.assertEqual(
            len(
                self.verify(
                    ("x", 1, " ".join(f"word{i}" for i in range(40))),
                    passages=(long_passage,),
                )
            ),
            1,
        )

    def test_markers_in_claim_text_are_removed(self):
        (claim,) = self.verify(
            ("Refund in 14 days [1][9].", 1, "within 14 days of purchase")
        )
        self.assertEqual(claim["text"], "Refund in 14 days .")

    def test_unusable_output_gives_no_claims(self):
        for output in (
            "sure",
            "null",
            "[]",
            '{"answer": "x [1]"}',
            '{"claims": "x"}',
            '{"claims": [1, "a", {"text": 5}]}',
            '{"claims": [{"text": "x"}]}',
        ):
            self.assertEqual(claim_service.verify_claims(output, [PASSAGE]), [], output)

    def test_at_most_the_limited_number_of_claims_and_cites(self):
        many = [("x", 1, "within 14 days of purchase")] * 20
        self.assertEqual(len(self.verify(*many)), 8)
        cites = [
            {"n": 1, "quote": q}
            for q in (
                "within 14 days of purchase",
                "request a refund within 14 days",
                "the original payment method",
                "aren’t refunded after they renew",
            )
        ]
        (claim,) = claim_service.verify_claims(
            json.dumps({"claims": [{"text": "x", "cites": cites}]}), [PASSAGE]
        )
        self.assertEqual(len(claim["cites"]), 3)

    def test_answer_text_has_markers_and_stops_before_the_limit(self):
        claims = [
            {"text": "One.", "cites": [{"n": 2}, {"n": 1}, {"n": 2}]},
            {"text": "Two.", "cites": [{"n": 3}]},
        ]
        self.assertEqual(claim_service.answer_text(claims), "One. [1][2] Two. [3]")
        big = [{"text": "x" * 1000, "cites": [{"n": 1}]}] * 2
        self.assertEqual(len(claim_service.answer_text(big)), 1004)
