from rest_framework.views import APIView

from ai.constants import messages
from ai.serializers.requests import UpdateSettingsSerializer
from ai.serializers.responses import LLMSettingsData
from ai.services import settings_service
from common.response.domain import ResourceUpdatedResponse, SuccessResponse
from common.throttling.scoped import AuthScopedThrottle, UserThrottle


class LLMSettingsView(APIView):
    """GET: the caller's own AI settings in this workspace. PATCH: change mode, model or key.
    The key is checked with the provider before it is saved and is never returned."""

    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "llm_settings"

    def get(self, request, workspace_id):
        row = settings_service.get_settings(request.user, workspace_id)
        return SuccessResponse(
            data=LLMSettingsData(row), message=messages.MESSAGE_SETTINGS_RETRIEVED
        )

    def patch(self, request, workspace_id):
        data = UpdateSettingsSerializer.parse(request.data)
        row = settings_service.update_settings(request.user, workspace_id, **data)
        return ResourceUpdatedResponse(
            data=LLMSettingsData(row), message=messages.MESSAGE_SETTINGS_UPDATED
        )


class LLMKeyView(APIView):
    """DELETE: forget the caller's own key (falls back to Resolve AI mode)."""

    def delete(self, request, workspace_id):
        row = settings_service.remove_key(request.user, workspace_id)
        return ResourceUpdatedResponse(
            data=LLMSettingsData(row), message=messages.MESSAGE_KEY_REMOVED
        )
