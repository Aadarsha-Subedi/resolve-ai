import itertools

from django.test import SimpleTestCase

from knowledge.constants.settings import (
    CHUNK_CODE_MAX_CHARS,
    CHUNK_HEADING_PATH_MAX_LENGTH,
    CHUNK_MAX_CHARS,
    CHUNK_MIN_CHARS,
)
from knowledge.services.chunker import chunk_document, chunk_markdown


def paths(chunks):
    return [c.heading_path for c in chunks]


class ChunkerStructureTests(SimpleTestCase):
    def test_empty_and_heading_only_articles_have_no_chunks(self):
        self.assertEqual(chunk_markdown("T", ""), [])
        self.assertEqual(chunk_markdown("T", "   \n\n"), [])
        self.assertEqual(chunk_markdown("T", "# Only\n## Headings\n"), [])

    def test_text_before_the_first_heading_uses_the_title(self):
        chunks = chunk_markdown("Billing", "Intro text.\n\n# Refunds\nRefund text.")
        self.assertEqual(paths(chunks), ["Billing", "Billing > Refunds"])
        self.assertEqual([c.text for c in chunks], ["Intro text.", "Refund text."])

    def test_nested_headings_build_the_path_and_siblings_reset_it(self):
        content = "# A\na\n## a1\nx\n### a1i\ny\n## a2\nz\n# B\nb"
        self.assertEqual(
            paths(chunk_markdown("T", content)),
            ["T > A", "T > A > a1", "T > A > a1 > a1i", "T > A > a2", "T > B"],
        )

    def test_only_levels_one_to_three_start_sections(self):
        chunks = chunk_markdown("T", "# A\ntext\n#### Deep\nmore")
        self.assertEqual(paths(chunks), ["T > A"])
        self.assertIn("#### Deep", chunks[0].text)

    def test_headings_inside_code_fences_are_text(self):
        content = "# A\n```\n# not a heading\nprint(1)\n```\nafter"
        chunks = chunk_markdown("T", content)
        self.assertEqual(paths(chunks), ["T > A"])
        self.assertIn("# not a heading", chunks[0].text)

    def test_a_first_heading_that_repeats_the_title_is_not_doubled(self):
        chunks = chunk_markdown("Refund policy", "# Refund policy\n\n## Annual\nText.")
        self.assertEqual(paths(chunks), ["Refund policy > Annual"])
        chunks = chunk_markdown("Refund Policy", "# refund policy\nText.")
        self.assertEqual(paths(chunks), ["Refund Policy"])
        chunks = chunk_markdown("Billing", "# Refunds\n## Refund policy\nText.")
        self.assertEqual(paths(chunks), ["Billing > Refunds > Refund policy"])

    def test_heading_path_is_capped(self):
        chunks = chunk_markdown("T" * 200, "# " + "h" * 400 + "\nbody")
        self.assertEqual(len(chunks[0].heading_path), CHUNK_HEADING_PATH_MAX_LENGTH)

    def test_output_is_deterministic(self):
        content = "# A\n" + "word " * 700 + "\n# B\nshort"
        self.assertEqual(chunk_markdown("T", content), chunk_markdown("T", content))


class ChunkerSizeTests(SimpleTestCase):
    def test_small_paragraphs_are_packed_together(self):
        content = "\n\n".join(f"Paragraph number {i} is short." for i in range(10))
        chunks = chunk_markdown("T", content)
        self.assertEqual(len(chunks), 1)
        self.assertIn("Paragraph number 9", chunks[0].text)

    def test_no_chunk_exceeds_the_maximum(self):
        sentence = "This sentence explains one idea clearly. "
        content = "# A\n" + sentence * 200 + "\n\n" + "word " * 1000
        for chunk in chunk_markdown("T", content):
            self.assertLessEqual(len(chunk.text), CHUNK_MAX_CHARS)

    def test_long_text_is_cut_at_sentence_boundaries(self):
        sentence = "This sentence explains one idea clearly."
        chunks = chunk_markdown("T", " ".join([sentence] * 100))
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertTrue(chunk.text.endswith("clearly."), chunk.text[-30:])

    def test_unbroken_strings_are_cut(self):
        chunks = chunk_markdown("T", "x" * 5000)
        self.assertTrue(all(len(c.text) <= CHUNK_MAX_CHARS for c in chunks))
        self.assertEqual(sum(len(c.text) for c in chunks), 5000)

    def test_a_tiny_last_piece_is_merged_backwards(self):
        first = "a" * (CHUNK_MAX_CHARS - 100)
        chunks = chunk_markdown("T", first + "\n\nlast bit")
        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].text.endswith("last bit"))

    def test_chunks_reach_the_minimum_when_there_is_enough_text(self):
        paragraph = "p" * 400
        chunks = chunk_markdown("T", "\n\n".join([paragraph] * 6))
        for chunk in chunks[:-1]:
            self.assertGreaterEqual(len(chunk.text), CHUNK_MIN_CHARS)


class ChunkerCodeBlockTests(SimpleTestCase):
    def test_a_code_block_stays_whole_and_keeps_its_blank_lines(self):
        code = "```python\ndef f():\n\n    return 1\n```"
        chunks = chunk_markdown("T", f"Before.\n\n{code}\n\nAfter.")
        joined = "\n".join(c.text for c in chunks)
        self.assertIn(code, joined)

    def test_a_medium_code_block_is_not_split(self):
        code = "```\n" + "\n".join(f"line {i}" for i in range(300)) + "\n```"
        self.assertLessEqual(len(code), CHUNK_CODE_MAX_CHARS)
        chunks = chunk_markdown("T", code)
        self.assertEqual([c.text for c in chunks], [code])

    def test_a_huge_code_block_is_cut_between_lines(self):
        code = "```\n" + "\n".join(f"line number {i}" for i in range(2000)) + "\n```"
        chunks = chunk_markdown("T", code)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.text), CHUNK_CODE_MAX_CHARS)
            for line in chunk.text.splitlines():
                self.assertTrue(line.startswith(("line number", "```")), line)


def table(rows: int) -> str:
    lines = ["| Plan | Price | Notes |", "| --- | --- | --- |"]
    lines += [f"| Plan {i} | ${i} | " + "details " * 12 + "|" for i in range(rows)]
    return "\n".join(lines)


class ChunkerTableTests(SimpleTestCase):
    def test_a_small_table_stays_whole(self):
        chunks = chunk_markdown("T", table(3))
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, table(3))

    def test_a_long_table_is_cut_between_rows_and_repeats_its_header(self):
        chunks = chunk_markdown("T", table(60))
        self.assertGreater(len(chunks), 1)
        header = "| Plan | Price | Notes |\n| --- | --- | --- |"
        rows = []
        for chunk in chunks:
            self.assertTrue(chunk.text.startswith(header), chunk.text[:40])
            self.assertLessEqual(len(chunk.text), CHUNK_MAX_CHARS)
            body = chunk.text[len(header) :].strip().splitlines()
            self.assertTrue(all(row.startswith("| Plan ") for row in body))
            rows += body
        self.assertEqual(len(rows), 60)  # every row exactly once
        self.assertEqual(rows[0].split("|")[1].strip(), "Plan 0")
        self.assertEqual(rows[-1].split("|")[1].strip(), "Plan 59")

    def test_text_that_only_looks_like_a_table_is_cut_as_text(self):
        block = "\n".join(["| not a table |"] * 200)
        for chunk in chunk_markdown("T", block):
            self.assertLessEqual(len(chunk.text), CHUNK_MAX_CHARS)

    def test_a_table_with_an_enormous_header_does_not_crash(self):
        header = "| " + " | ".join(["column"] * 200) + " |"
        block = "\n".join([header, "| --- |", *["| x |"] * 300])
        for chunk in chunk_markdown("T", block):
            self.assertLessEqual(len(chunk.text), CHUNK_MAX_CHARS)


SENTENCE = "This sentence explains one idea clearly."


class ChunkDocumentTests(SimpleTestCase):
    def test_pages_are_recorded_and_unnumbered_documents_have_none(self):
        chunks = chunk_document("Guide", [(1, "First page."), (2, "Second page.")])
        self.assertEqual(
            [(c.page, c.text) for c in chunks],
            [(1, "First page."), (2, "Second page.")],
        )
        plain = chunk_document("Guide", [(None, "Only text.")])
        self.assertEqual([c.page for c in plain], [None])

    def test_a_chunk_never_spans_two_pages(self):
        chunks = chunk_document("G", [(1, "Short one."), (2, "Short two.")])
        self.assertEqual(len(chunks), 2)

    def test_headings_carry_over_to_the_next_page(self):
        pages = [
            (1, "# Billing\n\n## Refunds\n\nRefunds take five days."),
            (2, "They are paid to the original card."),
            (3, "## Invoices\n\nInvoices are monthly."),
        ]
        chunks = chunk_document("Guide", pages)
        self.assertEqual(
            [(c.page, c.heading_path) for c in chunks],
            [
                (1, "Guide > Billing > Refunds"),
                (2, "Guide > Billing > Refunds"),
                (3, "Guide > Billing > Invoices"),
            ],
        )

    def test_empty_pages_produce_nothing(self):
        self.assertEqual(
            chunk_document("G", [(1, ""), (2, "  \n"), (3, "# Only heading")]), []
        )

    def test_a_cut_paragraph_overlaps_by_one_sentence_in_documents_only(self):
        text = " ".join([SENTENCE] * 100)
        plain = chunk_markdown("T", text)
        document = chunk_document("T", [(None, text)])
        for before, after in itertools.pairwise(document):
            self.assertTrue(before.text.endswith(SENTENCE))
            self.assertTrue(after.text.startswith(SENTENCE))
        for chunk in document:
            self.assertLessEqual(len(chunk.text), CHUNK_MAX_CHARS)
        # articles are unchanged: no sentence is repeated between passages
        self.assertEqual(" ".join(c.text for c in plain).count(SENTENCE), 100)
        self.assertGreater(" ".join(c.text for c in document).count(SENTENCE), 100)

    def test_overlap_is_skipped_when_the_sentence_is_too_long(self):
        long_sentence = ("word " * 40).strip() + "."  # about 200 characters
        text = " ".join([long_sentence] * 30)
        document = chunk_document("T", [(None, text)])
        joined = " ".join(c.text for c in document)
        self.assertEqual(joined.count(long_sentence), 30)

    def test_document_chunking_is_deterministic(self):
        pages = [(1, "# A\n" + "word " * 700), (2, table(40))]
        self.assertEqual(chunk_document("T", pages), chunk_document("T", pages))
