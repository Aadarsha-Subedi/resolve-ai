"""DOCX through python-docx, in this process.

Paragraphs, headings (Title and Heading 1-6 styles), bullet and numbered lists and tables are
kept, in document order. Images and charts are not read. A Word file has no fixed pages, so
the result is one unnumbered page.
"""

import io

from common.documents.base import (
    DocumentCorruptError,
    DocumentEmptyError,
    DocumentError,
    DocumentParser,
    DocumentTooLargeError,
    DocumentUnsupportedError,
    ParsedDocument,
    ParsedPage,
)
from common.documents.constants import (
    CONTENT_TYPE_DOCX,
    MAX_FILE_BYTES,
    MAX_MARKDOWN_CHARS,
)
from common.documents.markdown import table_to_markdown


class DocxParser(DocumentParser):
    def parse(self, data: bytes, content_type: str) -> ParsedDocument:
        if content_type != CONTENT_TYPE_DOCX:
            raise DocumentUnsupportedError()
        if len(data) > MAX_FILE_BYTES:
            raise DocumentTooLargeError()
        try:
            return self._convert(data)
        except DocumentError:
            raise
        except Exception as error:  # zip and XML errors come in many types
            raise DocumentCorruptError() from error

    def _convert(self, data: bytes) -> ParsedDocument:
        import docx
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        document = docx.Document(io.BytesIO(data))
        blocks: list[str] = []
        for item in document.iter_inner_content():
            if isinstance(item, Paragraph):
                block = _paragraph_markdown(item)
            elif isinstance(item, Table):
                block = table_to_markdown(
                    [[cell.text for cell in row.cells] for row in item.rows]
                )
            else:
                continue
            if block:
                blocks.append(block)
        markdown = "\n\n".join(blocks).replace("\x00", "").strip()
        if not markdown:
            raise DocumentEmptyError()
        if len(markdown) > MAX_MARKDOWN_CHARS:
            raise DocumentTooLargeError()
        return ParsedDocument(pages=(ParsedPage(number=None, markdown=markdown),))


def _paragraph_markdown(paragraph) -> str:
    text = paragraph.text.strip()
    if not text:
        return ""
    style = (paragraph.style.name or "") if paragraph.style is not None else ""
    if style == "Title":
        return f"# {text}"
    if style.startswith("Heading "):
        level = style.removeprefix("Heading ")
        if level.isdigit():
            return f"{'#' * min(int(level), 6)} {text}"
    if style.startswith("List Number"):
        return f"1. {text}"
    if style.startswith("List"):
        return f"- {text}"
    return text
