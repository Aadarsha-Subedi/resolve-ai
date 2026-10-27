CONTENT_TYPE_PDF = "application/pdf"
CONTENT_TYPE_DOCX = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
CONTENT_TYPE_MARKDOWN = "text/markdown"
CONTENT_TYPE_TEXT = "text/plain"

# Limits for one document (the upload limit of 10 MB is checked before this runs).
MAX_PAGES = 100
MAX_FILE_BYTES = 10 * 1024 * 1024
PARSE_TIMEOUT_SECONDS = 300  # a PDF still being read after this is refused as too slow
MAX_MARKDOWN_CHARS = 2_000_000  # extracted text above this is refused, not truncated

# PDF headings: a short line whose letters are at least this many times the body font size is a
# heading; the largest HEADING_MAX_LEVEL distinct sizes on a page become "#" to "###".
HEADING_MIN_SIZE_RATIO = 1.15
HEADING_MAX_LEVEL = 3
HEADING_MAX_CHARS = 100
