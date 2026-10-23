import io
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from common.documents import (
    DocumentCorruptError,
    DocumentEmptyError,
    DocumentTimeoutError,
    DocumentTooLargeError,
    DocumentUnsupportedError,
    docling_parser,
    get_parser,
)
from common.documents.constants import (
    CONTENT_TYPE_DOCX,
    CONTENT_TYPE_MARKDOWN,
    CONTENT_TYPE_PDF,
    CONTENT_TYPE_TEXT,
    MAX_FILE_BYTES,
)
from common.documents.docling_parser import DoclingParser
from common.documents.fake import FakeDocumentParser
from common.documents.text_parser import TextParser


class TextParserTests(SimpleTestCase):
    def test_text_and_markdown_pass_through(self):
        for content_type in (CONTENT_TYPE_TEXT, CONTENT_TYPE_MARKDOWN):
            parsed = TextParser().parse(b"\xef\xbb\xbf# Title\n\nBody\n", content_type)
            self.assertEqual(parsed.markdown, "# Title\n\nBody")
            self.assertEqual([page.number for page in parsed.pages], [None])

    def test_bad_bytes_and_nul_are_cleaned(self):
        parsed = TextParser().parse(b"caf\xe9\x00 ok", CONTENT_TYPE_TEXT)
        self.assertEqual(parsed.markdown, "caf� ok")

    def test_empty_unsupported_and_too_large(self):
        with self.assertRaises(DocumentEmptyError):
            TextParser().parse(b"  \n ", CONTENT_TYPE_TEXT)
        with self.assertRaises(DocumentUnsupportedError):
            TextParser().parse(b"x", CONTENT_TYPE_PDF)
        with (
            mock.patch("common.documents.text_parser.MAX_MARKDOWN_CHARS", 3),
            self.assertRaises(DocumentTooLargeError),
        ):
            TextParser().parse(b"abcd", CONTENT_TYPE_TEXT)


class FactoryAndFakeTests(SimpleTestCase):
    def test_routing(self):
        self.assertIsInstance(get_parser(CONTENT_TYPE_TEXT), TextParser)
        self.assertIsInstance(get_parser(CONTENT_TYPE_MARKDOWN), TextParser)
        self.assertIsInstance(get_parser(CONTENT_TYPE_PDF), DoclingParser)
        self.assertIsInstance(get_parser(CONTENT_TYPE_DOCX), DoclingParser)
        with self.assertRaises(DocumentUnsupportedError):
            get_parser("application/msword")

    def test_fake_parser_records_calls_and_fails_once(self):
        fake = FakeDocumentParser("# Hi")
        self.assertEqual(fake.parse(b"abc", CONTENT_TYPE_PDF).markdown, "# Hi")
        fake.fail_with = DocumentCorruptError()
        with self.assertRaises(DocumentCorruptError):
            fake.parse(b"abc", CONTENT_TYPE_PDF)
        fake.parse(b"abc", CONTENT_TYPE_PDF)
        self.assertEqual(len(fake.calls), 3)


def _result(status, pages=None, markdown_by_page=None, whole=""):
    document = mock.Mock()
    document.pages = {n: object() for n in (pages or [])}
    document.export_to_markdown.side_effect = lambda page_no=None: (
        (markdown_by_page or {}).get(page_no, "") if page_no else whole
    )
    return SimpleNamespace(status=status, document=document)


class DoclingParserMockedTests(SimpleTestCase):
    """The Docling call is replaced, so these test our handling of its results only."""

    def parse(self, result, content_type=CONTENT_TYPE_PDF, data=b"%PDF-1.4"):
        converter = mock.Mock()
        converter.convert.return_value = result
        with mock.patch.object(
            docling_parser, "_get_converter", return_value=converter
        ):
            return DoclingParser().parse(data, content_type), converter

    def test_pdf_pages_keep_their_numbers_and_empty_pages_are_dropped(self):
        from docling.datamodel.base_models import ConversionStatus

        result = _result(
            ConversionStatus.SUCCESS,
            pages=[1, 2, 3],
            markdown_by_page={1: "# A", 2: "  ", 3: "| x |\n| - |"},
        )
        parsed, converter = self.parse(result)
        self.assertEqual(
            [(p.number, p.markdown) for p in parsed.pages],
            [(1, "# A"), (3, "| x |\n| - |")],
        )
        _, kwargs = converter.convert.call_args
        self.assertEqual(kwargs["max_num_pages"], docling_parser.MAX_PAGES)
        self.assertEqual(kwargs["max_file_size"], MAX_FILE_BYTES)

    def test_docx_is_one_unnumbered_page(self):
        from docling.datamodel.base_models import ConversionStatus

        parsed, _ = self.parse(
            _result(ConversionStatus.SUCCESS, whole="# Policy\n\nText"),
            CONTENT_TYPE_DOCX,
            b"PK",
        )
        self.assertEqual(
            [(p.number, p.markdown) for p in parsed.pages], [(None, "# Policy\n\nText")]
        )

    def test_failures_map_to_our_errors(self):
        from docling.datamodel.base_models import ConversionStatus

        cases = (
            (_result(ConversionStatus.PARTIAL_SUCCESS), DocumentTimeoutError),
            (_result(ConversionStatus.FAILURE), DocumentCorruptError),
            (
                _result(ConversionStatus.SUCCESS, pages=[1], markdown_by_page={1: ""}),
                DocumentEmptyError,
            ),
        )
        for result, error in cases:
            with self.assertRaises(error):
                self.parse(result)

    def test_unexpected_exception_becomes_corrupt_and_oversize_is_refused(self):
        converter = mock.Mock()
        converter.convert.side_effect = RuntimeError("boom")
        with mock.patch.object(
            docling_parser, "_get_converter", return_value=converter
        ):
            with self.assertRaises(DocumentCorruptError):
                DoclingParser().parse(b"%PDF-", CONTENT_TYPE_PDF)
            with self.assertRaises(DocumentTooLargeError):
                DoclingParser().parse(b"x" * (MAX_FILE_BYTES + 1), CONTENT_TYPE_PDF)
        with self.assertRaises(DocumentUnsupportedError):
            DoclingParser().parse(b"x", CONTENT_TYPE_TEXT)


def _docx_with_heading_and_table() -> bytes:
    import docx

    document = docx.Document()
    document.add_heading("Refund policy", level=1)
    document.add_paragraph("Refunds are issued within 14 days.")
    document.add_heading("Plans", level=2)
    table = document.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Plan"
    table.rows[0].cells[1].text = "Price"
    table.rows[1].cells[0].text = "Pro"
    table.rows[1].cells[1].text = "$20"
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class DoclingRealDocxTests(SimpleTestCase):
    """Runs real Docling on a DOCX (no models are needed for Word files)."""

    def test_headings_and_tables_survive(self):
        markdown = (
            DoclingParser()
            .parse(_docx_with_heading_and_table(), CONTENT_TYPE_DOCX)
            .markdown
        )
        self.assertIn("# Refund policy", markdown)
        self.assertIn("## Plans", markdown)
        self.assertIn("| Plan", markdown)
        self.assertIn("$20", markdown)

    def test_garbage_is_corrupt(self):
        with self.assertRaises(DocumentCorruptError):
            DoclingParser().parse(b"PK\x03\x04 not really", CONTENT_TYPE_DOCX)


@unittest.skipUnless(
    os.environ.get("RESOLVE_AI_TEST_DOCLING_PDF"),
    "needs Docling's layout models (set RESOLVE_AI_TEST_DOCLING_PDF=path/to/sample.pdf)",
)
class DoclingRealPdfTests(SimpleTestCase):
    def test_pdf_is_converted_with_page_numbers(self):
        with open(os.environ["RESOLVE_AI_TEST_DOCLING_PDF"], "rb") as handle:
            parsed = DoclingParser().parse(handle.read(), CONTENT_TYPE_PDF)
        self.assertTrue(parsed.markdown)
        self.assertEqual(parsed.pages[0].number, 1)
