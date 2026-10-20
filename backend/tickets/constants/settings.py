SUBJECT_MAX_LENGTH = 200
TEXT_MAX_LENGTH = 20_000  # description and message bodies, plain text only
CUSTOMER_NAME_MAX_LENGTH = 100
DEFAULT_CATEGORY = "general"
DEFAULT_PRIORITY = "medium"

PORTAL_HONEYPOT_FIELD = "website"  # hidden field real customers never fill
PORTAL_EMAIL_LIMIT = 5  # tickets per customer email per workspace per window
PORTAL_EMAIL_WINDOW_SECONDS = 3600
PORTAL_EMAIL_CACHE_KEY = "portal:email:{workspace_id}:{email_hash}"
PORTAL_FAKE_NUMBER_RANGE = (100, 999)

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
