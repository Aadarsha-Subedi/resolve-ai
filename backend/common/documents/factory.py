"""Picks the parser for a file type. This is the only place that knows Docling."""

from common.documents.base import DocumentParser, DocumentUnsupportedError
from common.documents.constants import (
    CONTENT_TYPE_DOCX,
    CONTENT_TYPE_MARKDOWN,
    CONTENT_TYPE_PDF,
    CONTENT_TYPE_TEXT,
)
from common.documents.text_parser import TextParser


def get_parser(content_type: str) -> DocumentParser:
    if content_type in (CONTENT_TYPE_TEXT, CONTENT_TYPE_MARKDOWN):
        return TextParser()
    if content_type in (CONTENT_TYPE_PDF, CONTENT_TYPE_DOCX):
        from common.documents.docling_parser import DoclingParser  # heavy import

        return DoclingParser()
    raise DocumentUnsupportedError()
