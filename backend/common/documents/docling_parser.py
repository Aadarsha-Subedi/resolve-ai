"""PDF and DOCX through Docling, in this process (no separate service).

Docling is imported lazily and the converter is built once per process, because loading its
layout, table and OCR models takes seconds and memory. PDFs get layout analysis, table
structure and OCR for scanned pages; DOCX is read from its own structure.
"""

import io
import threading

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
    CONTENT_TYPE_DOCX,
    CONTENT_TYPE_PDF,
    MAX_FILE_BYTES,
    MAX_MARKDOWN_CHARS,
    MAX_PAGES,
    PARSE_TIMEOUT_SECONDS,
)

_converter = None
_converter_lock = threading.Lock()


def _build_converter():
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pdf_options = PdfPipelineOptions()
    pdf_options.do_ocr = True
    pdf_options.do_table_structure = True
    pdf_options.document_timeout = PARSE_TIMEOUT_SECONDS
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF, InputFormat.DOCX],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)},
    )


def _get_converter():
    global _converter
    with _converter_lock:
        if _converter is None:
            _converter = _build_converter()
        return _converter


class DoclingParser(DocumentParser):
    def parse(self, data: bytes, content_type: str) -> ParsedDocument:
        if content_type not in (CONTENT_TYPE_PDF, CONTENT_TYPE_DOCX):
            raise DocumentUnsupportedError()
        if len(data) > MAX_FILE_BYTES:
            raise DocumentTooLargeError()
        try:
            return self._convert(data, content_type)
        except DocumentError:
            raise
        except Exception as error:  # Docling raises many types; callers get one family
            raise DocumentCorruptError() from error

    def _convert(self, data: bytes, content_type: str) -> ParsedDocument:
        from docling.datamodel.base_models import ConversionStatus, DocumentStream

        name = "document.pdf" if content_type == CONTENT_TYPE_PDF else "document.docx"
        result = _get_converter().convert(
            DocumentStream(name=name, stream=io.BytesIO(data)),
            raises_on_error=False,
            max_num_pages=MAX_PAGES,
            max_file_size=MAX_FILE_BYTES,
        )
        if result.status == ConversionStatus.PARTIAL_SUCCESS:
            raise DocumentTimeoutError()  # the pipeline stopped at its time limit
        if result.status != ConversionStatus.SUCCESS:
            raise DocumentCorruptError()
        document = result.document
        if content_type == CONTENT_TYPE_PDF:
            page_numbers = sorted(document.pages)
            if len(page_numbers) > MAX_PAGES:
                raise DocumentTooLargeError()
            pages = tuple(
                ParsedPage(
                    number=number,
                    markdown=document.export_to_markdown(page_no=number).strip(),
                )
                for number in page_numbers
            )
            pages = tuple(page for page in pages if page.markdown)
        else:
            markdown = document.export_to_markdown().strip()
            pages = (ParsedPage(number=None, markdown=markdown),) if markdown else ()
        if not pages:
            raise DocumentEmptyError()
        if sum(len(page.markdown) for page in pages) > MAX_MARKDOWN_CHARS:
            raise DocumentTooLargeError()
        return ParsedDocument(pages=pages)
