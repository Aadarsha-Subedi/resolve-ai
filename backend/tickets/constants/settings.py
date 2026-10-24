SUBJECT_MAX_LENGTH = 200
TEXT_MAX_LENGTH = 20_000  # description and message bodies, plain text only
CUSTOMER_NAME_MAX_LENGTH = 100
DRAFT_INTENT_MAX_LENGTH = 200
AI_MAX_MESSAGES = 30  # newest public messages given to the LLM
AI_MESSAGE_MAX_CHARS = 2000  # each message is cut to this before it is sent
AI_SUMMARY_MAX_CHARS = 1500
AI_DRAFT_MAX_CHARS = 5000
AI_MAX_OUTPUT_TOKENS = 1024
DEFAULT_CATEGORY = "general"
DEFAULT_PRIORITY = "medium"

PORTAL_HONEYPOT_FIELD = "website"  # hidden field real customers never fill
PORTAL_EMAIL_LIMIT = 5  # tickets per customer email per workspace per window
PORTAL_EMAIL_WINDOW_SECONDS = 3600
PORTAL_EMAIL_CACHE_KEY = "portal:email:{workspace_id}:{email_hash}"
PORTAL_FAKE_NUMBER_RANGE = (100, 999)

ASSIGNEE_ME = "me"
ASSIGNEE_UNASSIGNED = "unassigned"

PRIORITY_RANK = {"low": 1, "medium": 2, "high": 3, "urgent": 4}
ORDERING_FIELDS = {
    "number",
    "created_at",
    "updated_at",
    "last_activity_at",
    "priority",
    "status",
}
DEFAULT_ORDERING = "-last_activity_at"
