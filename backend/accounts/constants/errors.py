"""Stable error codes: API `code` values and `?google_error=` redirect values."""

# Redirect codes used on /?google_error=<code>
GOOGLE_ERROR_CANCELLED = "cancelled"
GOOGLE_ERROR_FAILED = "google_failed"
GOOGLE_ERROR_RATE_LIMITED = "rate_limited"
GOOGLE_ERROR_EMAIL_UNVERIFIED = "email_unverified"
GOOGLE_ERROR_EMAIL_CONFLICT = "email_conflict"
GOOGLE_ERROR_ACCOUNT_DISABLED = "account_disabled"

# API error codes
ERROR_OWNERSHIP_BLOCKED = "account_owns_workspace"
ERROR_CANNOT_REVOKE_CURRENT = "cannot_revoke_current_session"
