from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.http import HttpResponseRedirect

from accounts.constants.settings import DEFAULT_APP_PATH, GOOGLE_ERROR_PARAM, LOGIN_PATH


def is_safe_next_path(value: str | None) -> bool:
    """Only same-site absolute paths: '/x' yes; '//host', '/\\host', 'http://x' no."""
    if not value or not value.startswith("/") or value.startswith(("//", "/\\")):
        return False
    parts = urlsplit(value)
    return not parts.scheme and not parts.netloc and "\\" not in value


def frontend_url(path: str) -> str:
    return settings.FRONTEND_URL.rstrip("/") + path


def app_redirect_url(next_path: str | None = None) -> str:
    return frontend_url(next_path if is_safe_next_path(next_path) else DEFAULT_APP_PATH)


def login_error_redirect(code: str) -> HttpResponseRedirect:
    query = urlencode({GOOGLE_ERROR_PARAM: code})
    return HttpResponseRedirect(f"{frontend_url(LOGIN_PATH)}?{query}")
