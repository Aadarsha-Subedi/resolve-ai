SCOPE_SEND = "https://www.googleapis.com/auth/gmail.send"
SCOPE_READ = "https://www.googleapis.com/auth/gmail.readonly"
REQUIRED_SCOPES = frozenset({SCOPE_SEND, SCOPE_READ})

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
HTTP_TIMEOUT_SECONDS = 15

SUBJECT_PREFIX = "Re: "
SUBJECT_MAX_LENGTH = 300
SNIPPET_MAX_LENGTH = 300
SENDER_NAME_MAX_LENGTH = 200
QUOTED_BODY_MAX_LENGTH = 20_000  # same limit as a ticket message
WATCH_RENEW_BEFORE_DAYS = 2
SEND_MAX_RETRIES = 3
SEND_RETRY_BACKOFF_SECONDS = 30
PORTAL_PATH = "/portal/{slug}"
INVITATIONS_PATH = "/app/invitations"

TASK_SEND_MESSAGE = "email_integration.send_ticket_message"
TASK_SEND_CONFIRMATION = "email_integration.send_portal_confirmation"
TASK_SEND_INVITATION = "email_integration.send_invitation_email"
TASK_SYNC_MAILBOX = "email_integration.sync_mailbox"
TASK_ENSURE_WATCH = "email_integration.ensure_gmail_watch"
TASK_RENEW_WATCHES = "email_integration.renew_gmail_watches"
TASK_PURGE_REVIEW = "email_integration.purge_old_review_items"

PUBSUB_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
