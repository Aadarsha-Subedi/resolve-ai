"""PDF through pdfplumber, in this process (no models, no OCR).

Text and tables are read page by page, so memory stays flat on long files. Tables become
Markdown tables placed after the page's other text. Scanned pages have no text layer and
give nothing; a PDF with no text at all is reported as empty. Images and charts are not read.
"""

import io
import time

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
    parts = [(text_page.extract_text() or "").strip()]
    parts.extend(table_to_markdown(table.extract()) for table in tables)
    return "\n\n".join(part for part in parts if part).replace("\x00", "")
