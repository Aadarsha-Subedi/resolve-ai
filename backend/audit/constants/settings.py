import re

ACTION_MAX_LENGTH = 50
TARGET_TYPE_MAX_LENGTH = 30
TARGET_ID_MAX_LENGTH = 64
ACTOR_NAME_MAX_LENGTH = 100

METADATA_MAX_JSON_LENGTH = 2000
METADATA_MAX_STRING_LENGTH = 200
METADATA_MAX_LIST_ITEMS = 20
# Keys whose values are never stored, whatever they hold.
SENSITIVE_KEY_PATTERN = re.compile(
    r"token|secret|password|passwd|credential|authorization|cookie|session|"
    r"\bkey\b|_key$|^key_|body|content|text|snippet|html|raw|signature",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
TRUNCATED_MARKER = {"truncated": True}
