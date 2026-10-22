from django.test import SimpleTestCase

from knowledge.constants.settings import (
    CHUNK_CODE_MAX_CHARS,
    CHUNK_HEADING_PATH_MAX_LENGTH,
    CHUNK_MAX_CHARS,
    CHUNK_MIN_CHARS,
)
from knowledge.services.chunker import chunk_markdown


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
