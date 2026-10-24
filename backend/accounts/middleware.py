import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from accounts.constants.settings import (
    SESSION_SEEN_KEY,
    SESSION_TOUCH_INTERVAL_SECONDS,
)


class SlidingSessionMiddleware:
    """Slides the session expiry at most once a minute per session, so ordinary traffic does
    not become a database and Redis write per request (SESSION_SAVE_EVERY_REQUEST is off).

    The last stamp lives in the session itself, which is already loaded, so the check costs
    no extra call. Stamping marks the session modified, and SessionMiddleware then saves it
    with a new expiry."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if not (
            request.session.session_key and user is not None and user.is_authenticated
        ):
            return response
        now = time.time()
        if now - request.session.get(SESSION_SEEN_KEY, 0) >= SESSION_TOUCH_INTERVAL_SECONDS:
            request.session[SESSION_SEEN_KEY] = now
        return response
