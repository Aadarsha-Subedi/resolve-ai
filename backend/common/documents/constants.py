CONTENT_TYPE_PDF = "application/pdf"
CONTENT_TYPE_DOCX = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
CONTENT_TYPE_MARKDOWN = "text/markdown"
CONTENT_TYPE_TEXT = "text/plain"

# Limits for one document (the upload limit of 10 MB is checked before this runs).
MAX_PAGES = 100
MAX_FILE_BYTES = 10 * 1024 * 1024
PARSE_TIMEOUT_SECONDS = (
    300  # the PDF pipeline stops after this and reports a partial result
)
MAX_MARKDOWN_CHARS = 2_000_000  # extracted text above this is refused, not truncated
