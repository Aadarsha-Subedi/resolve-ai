import re
from datetime import timedelta

SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])$")
SLUG_MIN_LENGTH = 3
SLUG_MAX_LENGTH = 40
SLUG_SUFFIX_BYTES = 2
SLUG_MAX_ATTEMPTS = 8
RESERVED_SLUGS = frozenset(
    {
        "admin", "api", "app", "health", "invitations", "join", "login", "logout",
        "media", "portal", "static", "support", "www", "workspaces",
    }
)  # fmt: skip
NAME_MAX_LENGTH = 80

# Postgres text search configurations a workspace may pick for full-text search. Every
# value must exist in `pg_ts_config` (a Postgres-only test checks this); "simple" does no
# stemming and drops no words, which suits mixed or unsupported languages.
SEARCH_LANGUAGE_CHOICES = (
    ("english", "English"),
    ("simple", "Simple (no stemming)"),
    ("spanish", "Spanish"),
    ("french", "French"),
    ("german", "German"),
    ("portuguese", "Portuguese"),
    ("italian", "Italian"),
    ("dutch", "Dutch"),
    ("danish", "Danish"),
    ("norwegian", "Norwegian"),
    ("swedish", "Swedish"),
    ("finnish", "Finnish"),
    ("russian", "Russian"),
    ("turkish", "Turkish"),
)
DEFAULT_SEARCH_LANGUAGE = "english"
SEARCH_LANGUAGE_MAX_LENGTH = 20

JOIN_LINK_EXPIRY_CHOICES: dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
}
JOIN_LINK_DEFAULT_EXPIRY = "1h"
JOIN_LINK_TOKEN_BYTES = 32
JOIN_LINK_URL_PATH = "/join/{token}"

INVITATION_EXPIRY = timedelta(days=7)
INVITATION_MAX_PER_REQUEST = 20

LOGO_MAX_BYTES = 2 * 1024 * 1024
LOGO_CONTENT_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}
LOGO_UPLOAD_URL_EXPIRY_SECONDS = 600
LOGO_KEY_PREFIX = "workspaces/{workspace_id}/logo/"

DEMO_WORKSPACE_NAME = "Demo: Fernway support"

TASK_PURGE_DELETED_WORKSPACES = "workspaces.purge_deleted_workspaces"
