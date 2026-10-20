import logging

from allauth.socialaccount.providers.google.views import oauth2_callback, oauth2_login
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
        if django_request.user.is_authenticated:
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
        # `next` is kept in our session and resolved against FRONTEND_URL; allauth must not see it.
        django_request.GET = django_request.GET.copy()
        django_request.GET.pop("next", None)
        return oauth2_login(django_request)


class GoogleCallbackView(GoogleFlowView):
    """GET /api/auth/google/login/callback/: Google's redirect target; allauth does the work."""

    def get(self, request):
        try:
            return oauth2_callback(request._request)
        except Exception:
            logger.exception("Unexpected error in the Google callback")
            return redirects.login_error_redirect(errors.GOOGLE_ERROR_FAILED)
