from rest_framework.views import APIView

from ai.constants import messages
from ai.serializers.requests import SaveKeySerializer, UpdateSettingsSerializer
from ai.serializers.responses import LLMSettingsData
from ai.services import settings_service
from common.response.domain import ResourceUpdatedResponse, SuccessResponse
from common.throttling.scoped import AuthScopedThrottle, UserThrottle


class LLMSettingsView(APIView):
    """GET: the caller's own AI settings in this workspace. PATCH: change the mode, the
    Resolve AI model or which saved key answers."""

    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "llm_settings"

    def get(self, request, workspace_id):
        view = settings_service.get_settings(request.user, workspace_id)
        return SuccessResponse(
            data=LLMSettingsData(view), message=messages.MESSAGE_SETTINGS_RETRIEVED
        )

    def patch(self, request, workspace_id):
        data = UpdateSettingsSerializer.parse(request.data)
        view = settings_service.update_settings(request.user, workspace_id, **data)
        return ResourceUpdatedResponse(
            data=LLMSettingsData(view), message=messages.MESSAGE_SETTINGS_UPDATED
        )


class LLMKeyView(APIView):
    """PUT: add the caller's key for a provider, or edit it (new key and/or model). The key is
    checked with the provider before it is saved and is never returned. DELETE: forget it."""

    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "llm_settings"

    def put(self, request, workspace_id, provider):
        data = SaveKeySerializer.parse(request.data)
        view = settings_service.save_key(request.user, workspace_id, provider, **data)
        return ResourceUpdatedResponse(
            data=LLMSettingsData(view), message=messages.MESSAGE_KEY_SAVED
        )

    def delete(self, request, workspace_id, provider):
        view = settings_service.remove_key(request.user, workspace_id, provider)
        return ResourceUpdatedResponse(
            data=LLMSettingsData(view), message=messages.MESSAGE_KEY_REMOVED
        )
