"""Plain text and Markdown files need no conversion: the text is the Markdown."""

from common.documents.base import (
    DocumentEmptyError,
    DocumentParser,
    DocumentTooLargeError,
    DocumentUnsupportedError,
    ParsedDocument,
    ParsedPage,
)
from common.documents.constants import (
    CONTENT_TYPE_MARKDOWN,
    CONTENT_TYPE_TEXT,
    MAX_MARKDOWN_CHARS,
)


class TextParser(DocumentParser):
    def parse(self, data: bytes, content_type: str) -> ParsedDocument:
        if content_type not in (CONTENT_TYPE_TEXT, CONTENT_TYPE_MARKDOWN):
            raise DocumentUnsupportedError()
        text = data.decode("utf-8-sig", errors="replace").replace("\x00", "").strip()
        if not text:
            raise DocumentEmptyError()
        if len(text) > MAX_MARKDOWN_CHARS:
            raise DocumentTooLargeError()
        return ParsedDocument(pages=(ParsedPage(number=None, markdown=text),))
