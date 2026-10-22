ARTICLE_TITLE_MAX_LENGTH = 200
ARTICLE_MAX_BYTES = 200 * 1024
CATEGORY_NAME_MAX_LENGTH = 60
CATEGORY_SLUG_MAX_LENGTH = 70
MAX_CATEGORIES_PER_ARTICLE = 10

# Passages the article is split into for search and citations.
CHUNK_MAX_CHARS = 1200
CHUNK_MIN_CHARS = 600
CHUNK_CODE_MAX_CHARS = 4800  # a fenced code block stays whole up to this size
CHUNK_MAX_HEADING_LEVEL = 3  # "#" to "###" start a new section
CHUNK_HEADING_PATH_MAX_LENGTH = 500
CHUNK_HEADING_SEPARATOR = " > "

DEFAULT_CATEGORIES = ["General", "Getting started", "Billing", "Troubleshooting", "FAQ"]

UPLOAD_MAX_BYTES = 10 * 1024 * 1024
UPLOAD_CONTENT_TYPES = {"application/pdf": "pdf", "text/plain": "txt"}
UPLOAD_FILENAME_MAX_LENGTH = 255
UPLOAD_URL_EXPIRY_SECONDS = 600
UPLOAD_PENDING_TTL_SECONDS = 3600  # unconfirmed uploads are cleaned up after this
DOWNLOAD_URL_EXPIRY_SECONDS = 300
PDF_MAGIC = b"%PDF-"

KEY_PREFIX = "workspaces/{workspace_id}/knowledge/"
UPLOAD_KEY = KEY_PREFIX + "uploads/{upload_id}.{extension}"

TASK_RELEASE_STALE_UPLOADS = "knowledge.release_stale_uploads"
