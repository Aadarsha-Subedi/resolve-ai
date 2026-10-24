"""Django settings for ResolveAI. Every RESOLVE_AI_* variable is required (see .env.example)."""

import os
import ssl
import sys
from pathlib import Path

import sentry_sdk
from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()

TESTING = "test" in sys.argv


def env(name: str) -> str:
    """Return a required env var; fail loudly when it is not set (empty is allowed)."""
    try:
        return os.environ[name]
    except KeyError:
        raise ImproperlyConfigured(f"Missing environment variable: {name}") from None


def env_bool(name: str) -> bool:
    return env(name).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str) -> list[str]:
    return [item.strip() for item in env(name).split(",") if item.strip()]


SECRET_KEY = env("RESOLVE_AI_SECRET_KEY")
DEBUG = env_bool("RESOLVE_AI_DEBUG")
ALLOWED_HOSTS = env_list("RESOLVE_AI_ALLOWED_HOSTS")
FRONTEND_URL = env("RESOLVE_AI_FRONTEND_URL")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # full-text search fields and indexes
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.usersessions",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "common",
    "accounts",
    "workspaces",
    "knowledge",
    "ai",
    "tickets",
    "email_integration",
    "audit",
]

MIDDLEWARE = [
    "common.observability.timing.RequestTimingMiddleware",
    "common.logger.request_id.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "allauth.usersessions.middleware.UserSessionsMiddleware",
    "common.logger.request_id.UserContextMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.logger.middleware.RequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database

if env_bool("RESOLVE_AI_USE_SQLITE"):
    # Escape hatch for running the test suite where Docker/Postgres is unavailable.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("RESOLVE_AI_DB_NAME"),
            "USER": env("RESOLVE_AI_DB_USER"),
            "PASSWORD": env("RESOLVE_AI_DB_PASSWORD"),
            "HOST": env("RESOLVE_AI_DB_HOST"),
            "PORT": env("RESOLVE_AI_DB_PORT"),
            "OPTIONS": {"sslmode": env("RESOLVE_AI_DB_SSLMODE")},
            "CONN_MAX_AGE": 600,
            "CONN_HEALTH_CHECKS": True,
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Email (system mail)

EMAIL_BACKEND = env("RESOLVE_AI_EMAIL_BACKEND")
DEFAULT_FROM_EMAIL = env("RESOLVE_AI_DEFAULT_FROM_EMAIL")

# Redis, cache and sessions

REDIS_URL = env("RESOLVE_AI_REDIS_URL")
REDIS_USES_TLS = REDIS_URL.startswith("rediss://")

if TESTING:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "cache",
        }
    }

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_AGE = 14 * 24 * 60 * 60  # 2 weeks, sliding
SESSION_REMEMBER_ME_AGE = 30 * 24 * 60 * 60  # 30 days, sliding
# Saved only when the session changes: saving on every request costs a database write and a Redis
# write per call. The 2-week (or 30-day remember-me) lifetime therefore counts from sign-in.
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_DOMAIN = env("RESOLVE_AI_COOKIE_DOMAIN") or None
CSRF_COOKIE_DOMAIN = SESSION_COOKIE_DOMAIN

SESSION_COOKIE_SECURE = env_bool("RESOLVE_AI_SECURE_COOKIES")
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_SSL_REDIRECT = env_bool("RESOLVE_AI_SSL_REDIRECT")
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REFERRER_POLICY = "same-origin"
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

CSRF_TRUSTED_ORIGINS = env_list("RESOLVE_AI_CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = env_list("RESOLVE_AI_CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# Throttle rates. Feature apps add their own named scopes here.

STRICT_THROTTLE_RATES = {
    "anon": "60/min",
    "user": "600/min",
    "google": "20/min",  # Google sign-in start and callback, per IP
    "gmail_sync": "6/min",  # manual "Sync latest mails", per user
    "account_delete": "5/hour",  # account deletion requests, per user
    "workspace": "1200/min",  # all users of one workspace together
    "portal_ticket": "10/hour",  # public ticket submission, per IP
    "join_link": "20/hour",  # join-link redemption, per IP
    "ai": "30/min",  # AI calls, per user
    "llm_settings": "10/min",  # AI settings reads and key checks, per user
    "dashboard": "30/min",  # dashboard reads, per user
    "webhook": "300/min",
}
RELAXED_THROTTLE_RATES = {
    **STRICT_THROTTLE_RATES,
    "anon": "600/min",
    "google": "600/min",
    "account_delete": "200/hour",
    "workspace": "6000/min",
    "portal_ticket": "200/hour",
    "join_link": "200/hour",
}
RELAX_THROTTLES = env_bool("RESOLVE_AI_RELAX_THROTTLES")
THROTTLE_RATES = (
    RELAXED_THROTTLE_RATES if RELAX_THROTTLES or TESTING else STRICT_THROTTLE_RATES
)

# Django REST framework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "common.exception.handler.exception_handler",
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": [
        "common.throttling.scoped.AnonThrottle",
        "common.throttling.scoped.UserThrottle",
        "common.throttling.scoped.WorkspaceThrottle",
    ],
    "NUM_PROXIES": int(env("RESOLVE_AI_NUM_PROXIES")),
    "DEFAULT_THROTTLE_RATES": THROTTLE_RATES,
}

# Accounts: django-allauth (Google only) with our own user model

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
GOOGLE_CLIENT_ID = env("RESOLVE_AI_GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = env("RESOLVE_AI_GOOGLE_CLIENT_SECRET")
PUBLIC_API_URL = env("RESOLVE_AI_PUBLIC_API_URL")  # origin the browser uses for /api
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
ACCOUNT_ADAPTER = "accounts.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.SocialAccountAdapter"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*"]
ACCOUNT_EMAIL_VERIFICATION = "none"  # Google verifies the address
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True  # no intermediate "continue" page
SOCIALACCOUNT_STORE_TOKENS = False  # the browser never gets Google tokens
SOCIALACCOUNT_ONLY = True
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": [
            {
                "client_id": GOOGLE_CLIENT_ID,
                "secret": GOOGLE_CLIENT_SECRET,
                "key": "",
            }
        ],
        # One sign-in flow: login plus Gmail (send and read). Gmail needs offline access
        # so Google hands back a refresh token (only on first consent or prompt=consent).
        "SCOPE": ["openid", "email", "profile", *GMAIL_SCOPES],
        "AUTH_PARAMS": {"prompt": "select_account", "access_type": "offline"},
        "OAUTH_PKCE_ENABLED": True,
    }
}
ACCOUNT_DELETION_GRACE_DAYS = 7

# Workspaces: deleted workspaces are purged after this many days

WORKSPACE_DELETION_GRACE_DAYS = 7

# Gmail push (Pub/Sub). All three empty = push disabled; the manual sync button still works.

GMAIL_PUBSUB_TOPIC = env(
    "RESOLVE_AI_GMAIL_PUBSUB_TOPIC"
)  # projects/<project>/topics/<topic>
PUBSUB_PUSH_AUDIENCE = env(
    "RESOLVE_AI_PUBSUB_PUSH_AUDIENCE"
)  # URL set on the push subscription
PUBSUB_PUSH_SERVICE_ACCOUNT = env(
    "RESOLVE_AI_PUBSUB_PUSH_SERVICE_ACCOUNT"
)  # signs push JWTs
GMAIL_MANUAL_SYNC_LIMIT = 30  # latest inbox messages read by "Sync latest mails"
GMAIL_REVIEW_MAX_PER_USER = 30  # newest unmatched messages kept for review
GMAIL_REVIEW_RETENTION_DAYS = 30

# Encryption keys for secrets at rest (Gmail refresh tokens, ...)

ENCRYPTION_KEYS = env_list("RESOLVE_AI_ENCRYPTION_KEYS")

# LLM calls. The Gemini key serves "Resolve AI" mode (empty disables it); the model is chosen
# by the user from common/llm/constants.py. The call limit is per user, per workspace, per day,
# and only counts calls on the Resolve AI key.
GEMINI_API_KEY = env("RESOLVE_AI_GEMINI_API_KEY")
LLM_CALL_LIMIT = int(env("RESOLVE_AI_LLM_CALL_LIMIT"))

# File storage (Cloudflare R2; empty bucket falls back to local disk)

R2_ENDPOINT_URL = env("RESOLVE_AI_R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID = env("RESOLVE_AI_R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = env("RESOLVE_AI_R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = env("RESOLVE_AI_R2_BUCKET_NAME")
R2_PUBLIC_BASE_URL = env("RESOLVE_AI_R2_PUBLIC_BASE_URL")

# Per-workspace knowledge-base upload limit (decided: 50 MB)

WORKSPACE_STORAGE_QUOTA_BYTES = 50 * 1024 * 1024
# Most knowledge articles (any status) one workspace can hold.
WORKSPACE_MAX_ARTICLES = 100
# Most workspaces one user can belong to, counting both created and joined ones.
USER_MAX_WORKSPACES = 5

# Sentry (error monitoring only; empty DSN disables it)

SENTRY_DSN = env("RESOLVE_AI_SENTRY_DSN")
ENVIRONMENT = env("RESOLVE_AI_ENVIRONMENT").strip().lower()
if ENVIRONMENT not in {"local", "prod"}:
    raise ImproperlyConfigured("RESOLVE_AI_ENVIRONMENT must be local or prod.")
IS_PRODUCTION = ENVIRONMENT == "prod"
if SENTRY_DSN and not TESTING:
    from common.observability.sentry import before_send

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENVIRONMENT,
        send_default_pii=False,
        before_send=before_send,
        traces_sample_rate=0.0,
    )

# Celery

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
if REDIS_USES_TLS:
    CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
    CELERY_REDIS_BACKEND_USE_SSL = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
CELERY_TASK_ALWAYS_EAGER = TESTING
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_DATA_DIR = BASE_DIR / ".celery"
CELERY_DATA_DIR.mkdir(exist_ok=True)
CELERY_BEAT_SCHEDULE_FILENAME = str(CELERY_DATA_DIR / "celerybeat-schedule")
CELERY_BEAT_SCHEDULE: dict = {  # feature apps register their periodic tasks here
    "accounts-purge-deleted-accounts": {
        "task": "accounts.purge_deleted_accounts",
        "schedule": crontab(hour=3, minute=0),
    },
    "workspaces-purge-deleted-workspaces": {
        "task": "workspaces.purge_deleted_workspaces",
        "schedule": crontab(hour=4, minute=0),
    },
    "knowledge-release-stale-uploads": {
        "task": "knowledge.release_stale_uploads",
        "schedule": crontab(minute=15),
    },
    "knowledge-requeue-unindexed-uploads": {
        "task": "knowledge.requeue_unindexed_uploads",
        "schedule": crontab(minute="*/10"),
    },
    "knowledge-embed-pending-chunks": {
        "task": "knowledge.embed_pending_chunks",
        "schedule": crontab(minute="*/15"),
    },
    "email-renew-gmail-watches": {
        "task": "email_integration.renew_gmail_watches",
        "schedule": crontab(hour=2, minute=30),
    },
    "email-purge-old-review-items": {
        "task": "email_integration.purge_old_review_items",
        "schedule": crontab(hour=3, minute=45),
    },
    "accounts-clear-expired-sessions": {
        "task": "accounts.clear_expired_sessions",
        "schedule": crontab(hour=3, minute=30),
    },
}

# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "common.logger.request_id.RequestIdFilter"},
    },
    "formatters": {
        "color": {
            "()": "common.logger.formatters.ColorFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
        },
        "json": {"()": "common.logger.formatters.JSONFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "color" if DEBUG else "json",
            "filters": ["request_id"],
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
