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
# Uploaded documents: when a long paragraph must be cut, the next passage starts with the last
# sentence of the previous one if it is at most this long (context for search and embeddings).
CHUNK_OVERLAP_CHARS = 150

# Context search (citations for a ticket, a customer message or a chat question)
CONTEXT_QUERY_MIN_LENGTH = 2
CONTEXT_QUERY_MAX_LENGTH = 2000
CONTEXT_MAX_RESULTS = 5
# Passages taken from each query's ranking before merging.
CONTEXT_CANDIDATES_PER_QUERY = 20
# ts_rank_cd (0..1). A lone word found only in a passage's body scores about 0.29 and a word
# in its heading path about 0.5 or more. With few search words any match counts; with many,
# one stray body word is noise, so the bar is raised just above it.
CONTEXT_MIN_SCORE = 0.05
CONTEXT_MIN_SCORE_MANY_TERMS = 0.3
CONTEXT_MANY_TERMS = 3
# BM25 (ParadeDB `pg_search`). BM25 scores depend on the size of the corpus (IDF), so there is
# no fixed score floor. A passage counts when the query's words occur in it at least this many
# times (`bm25_terms` repeats a word per occurrence and counts a heading word twice): one body
# word is noise when the query has many words, a heading word or two body words are not.
CONTEXT_BM25_MIN_HITS = 1
CONTEXT_BM25_MIN_HITS_MANY_TERMS = 2
# Candidates read from the BM25 index per query before the visibility filter (drafts and
# archived articles are dropped afterwards); the best CONTEXT_CANDIDATES_PER_QUERY are kept.
CONTEXT_BM25_POOL = 100
# A heading word counts this many times in `bm25_terms`, so a heading hit outweighs a body hit
# (the BM25 counterpart of the weight-A heading in `search_vector`).
BM25_HEADING_BOOST = 2
# Vector search: a passage counts when its cosine similarity to the query is at least this.
# Not tuned on real data yet; raise it if unrelated passages appear, lower it if related
# ones are missed.
CONTEXT_MIN_SIMILARITY = 0.55
# Searches that embed their query text (original + rewrites go in one request) are limited
# per user, per workspace, per UTC day. They use the Resolve AI key whatever the user's mode.
EMBED_QUERY_DAILY_LIMIT = 300
EMBED_QUERY_USAGE_KEY = "knowledge:query-embeddings:{workspace_id}:{user_id}:{day}"
CONTEXT_RRF_K = 60  # reciprocal rank fusion: score = sum of 1 / (K + rank)
# Reranking (Cohere): the best fused passages are sent to the reranker, which reads the question
# and each passage together; the best CONTEXT_MAX_RESULTS by its score are kept. Skipped (the
# fused order is used) with no key, over the daily limit or on any provider error.
CONTEXT_RERANK_CANDIDATES = 25
# Passages whose rerank score is below this are dropped (0 = off). 0.05 sits above the noise
# seen on real queries (0.002 to 0.03) and below every relevant passage (0.26 and up).
CONTEXT_RERANK_MIN_SCORE = 0.05
# Reranked searches are counted per workspace per UTC day (the limit is RERANK_DAILY_LIMIT).
RERANK_USAGE_KEY = "knowledge:rerank:{workspace_id}:{day}"
# The same text is not sent to the LLM twice within this time.
CONTEXT_REWRITE_CACHE_SECONDS = 60 * 60
CONTEXT_REWRITE_CACHE_KEY = "knowledge:rewrites:{workspace_id}:{digest}"

DEFAULT_CATEGORIES = ["General", "Getting started", "Billing", "Troubleshooting", "FAQ"]

UPLOAD_MAX_BYTES = 10 * 1024 * 1024
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
UPLOAD_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
    DOCX_CONTENT_TYPE: "docx",
}
UPLOAD_FILENAME_MAX_LENGTH = 255
UPLOAD_URL_EXPIRY_SECONDS = 600
UPLOAD_PENDING_TTL_SECONDS = 3600  # unconfirmed uploads are cleaned up after this
DOWNLOAD_URL_EXPIRY_SECONDS = 300
PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"  # a DOCX is a zip archive
# DOCX archives are checked from the zip directory only (nothing is decompressed here).
DOCX_REQUIRED_PARTS = ("[Content_Types].xml", "word/document.xml")
DOCX_MAX_ENTRIES = 1000
DOCX_MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024  # declared size of all parts together

KEY_PREFIX = "workspaces/{workspace_id}/knowledge/"
UPLOAD_KEY = KEY_PREFIX + "uploads/{upload_id}.{extension}"
# Markdown extracted from an upload. Derived data: it does not count toward the quota.
EXTRACTED_KEY = KEY_PREFIX + "uploads/{upload_id}.extracted.md"
EXTRACTED_CONTENT_TYPE = "text/markdown; charset=utf-8"

TASK_RELEASE_STALE_UPLOADS = "knowledge.release_stale_uploads"
TASK_REINDEX_WORKSPACE = "knowledge.reindex_workspace"
TASK_INDEX_UPLOAD = "knowledge.index_upload"
TASK_REQUEUE_UNINDEXED_UPLOADS = "knowledge.requeue_unindexed_uploads"

# Reading a document runs on the default queue, with the same worker as everything else.
INDEX_QUEUE = "default"
INDEX_SOFT_TIME_LIMIT_SECONDS = 330  # a little above the document parser's own 300 s
INDEX_TIME_LIMIT_SECONDS = 360
INDEX_MAX_RETRIES = 2
INDEX_RETRY_BACKOFF_SECONDS = 60
# An INDEXING upload not touched for this long is treated as abandoned (worker died).
INDEX_STALE_SECONDS = 15 * 60
# The sweeper re-queues uploads still waiting for their first run after this long.
INDEX_REQUEUE_AFTER_SECONDS = 10 * 60
INDEX_ERROR_FAILED = (
    "index_failed"  # stored for unexpected errors; others use DocumentError codes
)
INDEX_ERROR_TIMEOUT = "document_timeout"

ANSWER_MAX_CHARS = 1500
ANSWER_MAX_OUTPUT_TOKENS = 1024

ASK_TITLE_MAX_LENGTH = 80
ASK_MAX_CONVERSATIONS = 50  # per user per workspace; the oldest are removed beyond this
ASK_MAX_TURNS = 50  # per conversation

TASK_EMBED_SOURCE = "knowledge.embed_source"
TASK_EMBED_PENDING_CHUNKS = "knowledge.embed_pending_chunks"
EMBED_SOURCE_ARTICLE = "article"
EMBED_SOURCE_UPLOAD = "upload"
EMBED_SOURCES = (EMBED_SOURCE_ARTICLE, EMBED_SOURCE_UPLOAD)
EMBED_MAX_RETRIES = 3
EMBED_RETRY_BACKOFF_SECONDS = 60
# The Resolve AI key pays for embeddings, so each workspace may embed this many chunks per
# UTC day (about 24 MB of text). What is over the cap waits for the next day's sweep.
EMBED_DAILY_CHUNK_LIMIT = 20_000
EMBED_USAGE_KEY = "knowledge:embeddings:{workspace_id}:{day}"
EMBED_USAGE_TTL_SECONDS = 2 * 24 * 60 * 60
# The sweeper queues at most this many articles/uploads per run.
EMBED_SWEEP_SOURCES = 50
# Verified claims: the model returns claims with the exact quote that backs each one, and a
# claim is shown only when a quote is found in the passage it cites.
CLAIM_MAX_CLAIMS = 8
CLAIM_TEXT_MAX_CHARS = 400
CLAIM_MAX_CITES = 3
CLAIM_QUOTE_MIN_WORDS = 3
CLAIM_QUOTE_MAX_WORDS = 40
CLAIM_CONTEXT_CHARS = (
    160  # passage text kept before and after a quote, to show it in place
)

# Semantic cache of answers: a question whose embedding is at least this similar (cosine) to a
# cached question of the same workspace, answered by the same provider and model, gets the
# cached answer with no search and no LLM call. Not tuned on real data yet: every hit logs its
# similarity in the AI usage log; raise it if wrong answers are served, lower it if near
# repeats miss.
CACHE_MIN_SIMILARITY = 0.92
CACHE_TTL_DAYS = 7
