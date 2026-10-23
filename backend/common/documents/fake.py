"""In-memory parser for tests. Queue a result or an error, inspect `calls`."""

from common.documents.base import (
    DocumentError,
    DocumentParser,
    ParsedDocument,
    ParsedPage,
)


class FakeDocumentParser(DocumentParser):
    def __init__(self, markdown: str = "# Fake\n\nText"):
        self.markdown = markdown
        self.calls: list[tuple[int, str]] = []
        self.fail_with: DocumentError | None = None  # raised by the next call

    def parse(self, data: bytes, content_type: str) -> ParsedDocument:
        self.calls.append((len(data), content_type))
        if self.fail_with is not None:
            error, self.fail_with = self.fail_with, None
            raise error
        return ParsedDocument(pages=(ParsedPage(number=None, markdown=self.markdown),))
