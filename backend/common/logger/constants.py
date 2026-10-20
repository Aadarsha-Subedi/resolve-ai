import logging

SENSITIVE_KEYS = {
    "password",
    "passwd",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "auth",
    "secret",
    "api_key",
    "encrypted_token",
    "bot_token",
    "client_secret",
    "signing_secret",
    "apikey",
    "card_number",
    "cvv",
    "ssn",
    "credit_card",
}

REDACTED = "***REDACTED***"

COLORS = {
    logging.DEBUG: "\033[33m",  # yellow — inline debugging
    logging.INFO: "\033[32m",  # green — standard logs
    logging.WARNING: "\033[33m",  # yellow
    logging.ERROR: "\033[31m",  # red — exceptions / errors
    logging.CRITICAL: "\033[41m",  # red background — severe
}
RESET_COLOR = "\033[0m"
