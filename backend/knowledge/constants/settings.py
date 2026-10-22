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

# Context search (citations for a ticket, a customer message or a chat question)
CONTEXT_QUERY_MIN_LENGTH = 2
CONTEXT_QUERY_MAX_LENGTH = 2000
CONTEXT_MAX_RESULTS = 5
CONTEXT_MAX_PER_ARTICLE = 2
# Passages taken from each query's ranking before merging.
CONTEXT_CANDIDATES_PER_QUERY = 20
# ts_rank_cd (0..1). A lone word found only in a passage's body scores about 0.29 and a word
# in its heading path about 0.5 or more. With few search words any match counts; with many,
# one stray body word is noise, so the bar is raised just above it.
CONTEXT_MIN_SCORE = 0.05
CONTEXT_MIN_SCORE_MANY_TERMS = 0.3
CONTEXT_MANY_TERMS = 3
CONTEXT_RRF_K = 60  # reciprocal rank fusion: score = sum of 1 / (K + rank)
# The same text is not sent to the LLM twice within this time.
CONTEXT_REWRITE_CACHE_SECONDS = 60 * 60
CONTEXT_REWRITE_CACHE_KEY = "knowledge:rewrites:{workspace_id}:{digest}"

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
TASK_REINDEX_WORKSPACE = "knowledge.reindex_workspace"

ANSWER_MAX_CHARS = 1500
ANSWER_MAX_OUTPUT_TOKENS = 1024

ASK_TITLE_MAX_LENGTH = 80
ASK_MAX_CONVERSATIONS = 50  # per user per workspace; the oldest are removed beyond this
ASK_MAX_TURNS = 50  # per conversation
