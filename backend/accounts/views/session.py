from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from accounts.constants import messages
from accounts.serializers.responses import MessageData, SessionData
from accounts.services import session_service
from common.response.domain import (
    ListResponseData,
    ResourceDeletedResponse,
    ResourceListResponse,
    SuccessResponse,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """GET /api/csrf/: sets the CSRF cookie the frontend echoes in X-CSRFToken."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        return SuccessResponse(message=messages.MESSAGE_CSRF_SET)


class LogoutView(APIView):
    def post(self, request):
        session_service.logout_current(request._request)
        return SuccessResponse(message=messages.MESSAGE_LOGGED_OUT)


class LogoutAllView(APIView):
    def post(self, request):
        session_service.logout_everywhere(request._request)
        return SuccessResponse(message=messages.MESSAGE_LOGGED_OUT_ALL)


class SessionListView(APIView):
    def get(self, request):
        current_key = request.session.session_key
        items = [
            SessionData(session=s, is_current=s.session_key == current_key)
            for s in session_service.list_sessions(request.user)
        ]
        return ResourceListResponse(
            data=ListResponseData(items=items),
            message=messages.MESSAGE_SESSIONS_LISTED,
        )


class SessionDetailView(APIView):
    def delete(self, request, session_id: int):
        session_service.revoke_session(request._request, request.user, session_id)
        return ResourceDeletedResponse(
            data=MessageData(), message=messages.MESSAGE_SESSION_REVOKED
        )
