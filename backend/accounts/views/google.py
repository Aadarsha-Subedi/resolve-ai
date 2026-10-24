import logging

from allauth.socialaccount.providers.google.views import oauth2_callback, oauth2_login
from django.contrib.auth import get_user
from django.http import HttpResponseRedirect
from rest_framework.exceptions import Throttled
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from accounts import redirects
from accounts.constants import errors
from accounts.constants.settings import SESSION_NEXT_KEY, SESSION_REMEMBER_KEY
from common.throttling.scoped import AnonThrottle, AuthScopedThrottle

logger = logging.getLogger(__name__)


class GoogleFlowView(APIView):
    """Shared by the two browser-facing Google endpoints: throttled per IP, never JSON."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonThrottle, AuthScopedThrottle]
    throttle_scope = "google"

    def handle_exception(self, exc):
        if isinstance(exc, Throttled):
            return redirects.login_error_redirect(errors.GOOGLE_ERROR_RATE_LIMITED)
        return super().handle_exception(exc)


class GoogleStartView(GoogleFlowView):
    """GET /api/auth/google/start/?remember=0|1&next=/path: begin sign-in."""

    def get(self, request):
        django_request = request._request
        reconnect = request.query_params.get("reconnect") == "1"
        # DRF replaces request.user with AnonymousUser when a view has no authenticators, so
        # ask the session directly.
        if get_user(django_request).is_authenticated and not reconnect:
            return HttpResponseRedirect(
                redirects.app_redirect_url(request.query_params.get("next"))
            )
        session = django_request.session
        session[SESSION_REMEMBER_KEY] = request.query_params.get("remember") == "1"
        next_path = request.query_params.get("next")
        if redirects.is_safe_next_path(next_path):
            session[SESSION_NEXT_KEY] = next_path
        else:
            session.pop(SESSION_NEXT_KEY, None)
        # allauth must not see `next` (resolved against FRONTEND_URL by our adapter), nor
        # caller-chosen scopes or auth params. `reconnect=1` forces Google's consent screen,
        # which is the only way to get a fresh Gmail refresh token for an existing grant.
        django_request.GET = django_request.GET.copy()
        for name in ("next", "scope", "auth_params", "process"):
            django_request.GET.pop(name, None)
        if reconnect:
            django_request.GET["auth_params"] = "prompt=consent"
        return oauth2_login(django_request)


class GoogleCallbackView(GoogleFlowView):
    """GET /api/auth/google/login/callback/: Google's redirect target; allauth does the work."""

    def get(self, request):
        try:
            return oauth2_callback(request._request)
        except Exception:
            logger.exception("Unexpected error in the Google callback")
            return redirects.login_error_redirect(errors.GOOGLE_ERROR_FAILED)
