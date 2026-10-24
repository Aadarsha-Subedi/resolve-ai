"""The parser interface and the errors every parser maps its failures to."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class DocumentError(Exception):
    """Base class. Messages are generic on purpose: they never contain document text."""

    code = "document_error"
    message = "The document could not be read."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)


class DocumentUnsupportedError(DocumentError):
    code = "document_unsupported"
    message = "This file type cannot be read."


class DocumentTooLargeError(DocumentError):
    code = "document_too_large"
    message = "The document has too many pages or too much text."


class DocumentTimeoutError(DocumentError):
    code = "document_timeout"
    message = "Reading the document took too long."


class DocumentEmptyError(DocumentError):
    code = "document_empty"
    message = "No readable text was found in the document."


class DocumentCorruptError(DocumentError):
    code = "document_corrupt"
    message = "The file is damaged or not a valid document."


@dataclass(frozen=True)
class ParsedPage:
    """Markdown of one page. `number` is 1-based for PDFs and None where pages do not exist."""

    number: int | None
    markdown: str


@dataclass(frozen=True)
class ParsedDocument:
    pages: tuple[ParsedPage, ...]

    @property
    def markdown(self) -> str:
        return "\n\n".join(page.markdown for page in self.pages)


class DocumentParser(ABC):
    """Role: turn an uploaded file into Markdown (headings, tables, page numbers kept).
    Callers depend on this; `get_parser` picks the concrete class."""

    @abstractmethod
    def parse(self, data: bytes, content_type: str) -> ParsedDocument:
        """Raises a DocumentError subclass on any failure."""
