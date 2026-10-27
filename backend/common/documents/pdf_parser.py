"""PDF through pdfplumber, in this process (no models, no OCR).

Text and tables are read page by page, so memory stays flat on long files. Tables become
Markdown tables placed after the page's other text. A short line set in a clearly larger font
than the page's body text is written as a Markdown heading (`#` to `###`, the largest size
first), so the chunker can start sections there. Scanned pages have no text layer and
give nothing; a PDF with no text at all is reported as empty. Images and charts are not read.
"""

import io
import time
from collections import Counter

from common.documents.base import (
    DocumentCorruptError,
    DocumentEmptyError,
    DocumentError,
    DocumentParser,
    DocumentTimeoutError,
    DocumentTooLargeError,
    DocumentUnsupportedError,
    ParsedDocument,
    ParsedPage,
)
from common.documents.constants import (
    CONTENT_TYPE_PDF,
    HEADING_MAX_CHARS,
    HEADING_MAX_LEVEL,
    HEADING_MIN_SIZE_RATIO,
    MAX_FILE_BYTES,
    MAX_MARKDOWN_CHARS,
    MAX_PAGES,
    PARSE_TIMEOUT_SECONDS,
)
from common.documents.markdown import table_to_markdown


class PdfParser(DocumentParser):
    def parse(self, data: bytes, content_type: str) -> ParsedDocument:
        if content_type != CONTENT_TYPE_PDF:
            raise DocumentUnsupportedError()
        if len(data) > MAX_FILE_BYTES:
            raise DocumentTooLargeError()
        try:
            return self._convert(data)
        except DocumentError:
            raise
        except Exception as error:  # pdfminer raises many types; callers get one family
            raise DocumentCorruptError() from error

    def _convert(self, data: bytes) -> ParsedDocument:
        import pdfplumber

        deadline = time.monotonic() + PARSE_TIMEOUT_SECONDS
        pages: list[ParsedPage] = []
        total_chars = 0
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if len(pdf.pages) > MAX_PAGES:
                raise DocumentTooLargeError()
            for number, page in enumerate(pdf.pages, start=1):
                if time.monotonic() > deadline:
                    raise DocumentTimeoutError()
                markdown = _page_markdown(page)
                page.flush_cache()
                if not markdown:
                    continue
                total_chars += len(markdown)
                if total_chars > MAX_MARKDOWN_CHARS:
                    raise DocumentTooLargeError()
                pages.append(ParsedPage(number=number, markdown=markdown))
        if not pages:
            raise DocumentEmptyError()
        return ParsedDocument(pages=tuple(pages))


def _page_markdown(page) -> str:
    tables = page.find_tables()
    text_page = page
    for table in tables:
        text_page = text_page.outside_bbox(table.bbox)  # the table text is added below
    parts = [_page_text(text_page)]
    parts.extend(table_to_markdown(table.extract()) for table in tables)
    return "\n\n".join(part for part in parts if part).replace("\x00", "")


def _page_text(page) -> str:
    """The page's text with large-font lines turned into Markdown headings."""
    lines = page.extract_text_lines(return_chars=True, strip=True)
    if not lines:
        return ""
    sizes = Counter()
    for line in lines:
        for char in line["chars"]:
            if char["text"].strip():
                sizes[round(char["size"], 1)] += 1
    if not sizes:
        return ""
    body = sizes.most_common(1)[0][0]
    larger = sorted(
        {size for size in sizes if size >= body * HEADING_MIN_SIZE_RATIO},
        reverse=True,
    )[:HEADING_MAX_LEVEL]
    out: list[str] = []
    for line in lines:
        text = " ".join(line["text"].split())
        if not text:
            continue
        level = _heading_level(line, text, larger)
        if level:
            out.extend(["", f"{'#' * level} {text}", ""])
        else:
            out.append(text)
    return "\n".join(out).strip()


def _heading_level(line, text: str, larger: list[float]) -> int:
    """1 to HEADING_MAX_LEVEL when the line is short, does not end like a sentence and its
    largest letters are in one of the `larger` sizes; 0 otherwise."""
    if not larger or len(text) > HEADING_MAX_CHARS or text.endswith((".", ",", ";")):
        return 0
    size = max(
        (round(c["size"], 1) for c in line["chars"] if c["text"].strip()), default=0
    )
    return larger.index(size) + 1 if size in larger else 0
