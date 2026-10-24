from django.conf import settings
from rest_framework.views import APIView

from accounts.constants import messages
from accounts.serializers.requests import UpdateProfileSerializer
from accounts.serializers.responses import MessageData, ProfileData
from accounts.services import deletion_service, profile_service
from common.response.domain import ResourceUpdatedResponse, SuccessResponse
from common.throttling.scoped import AnonThrottle, AuthScopedThrottle, UserThrottle


class MeView(APIView):
    """GET/PATCH/DELETE /api/me/: own profile and account deletion."""

    throttle_classes = [AnonThrottle, UserThrottle, AuthScopedThrottle]

    def get_throttles(self):
        # Only deletion gets the stricter named scope.
        self.throttle_scope = (
            "account_delete" if self.request.method == "DELETE" else None
        )
        return super().get_throttles()

    def get(self, request):
        return SuccessResponse(
            data=ProfileData(user=request.user),
            message=messages.MESSAGE_PROFILE_RETRIEVED,
        )

    def patch(self, request):
        data = UpdateProfileSerializer.parse(request.data)
        user = profile_service.update_display_name(request.user, data["display_name"])
        return ResourceUpdatedResponse(
            data=ProfileData(user=user), message=messages.MESSAGE_PROFILE_UPDATED
        )

    def delete(self, request):
        deletion_service.request_deletion(request._request, request.user)
        return SuccessResponse(
            data=MessageData(),
            message=messages.MESSAGE_DELETION_REQUESTED.format(
                days=settings.ACCOUNT_DELETION_GRACE_DAYS
            ),
        )
