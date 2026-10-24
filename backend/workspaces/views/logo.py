from rest_framework.views import APIView

from common.response.domain import ResourceDeletedResponse, SuccessResponse
from workspaces.constants import messages
from workspaces.serializers.requests import (
    ConfirmLogoSerializer,
    LogoUploadUrlSerializer,
)
from workspaces.serializers.responses import DictData, WorkspaceData
from workspaces.services import access, logo_service


class LogoUploadUrlView(APIView):
    """POST: get a signed URL; the browser PUTs the image there, then confirms with PUT /logo/."""

    def post(self, request, workspace_id):
        data = LogoUploadUrlSerializer.parse(request.data)
        payload = logo_service.create_upload_url(
            request.user, workspace_id, data["content_type"], data["size"]
        )
        return SuccessResponse(
            data=DictData(payload), message=messages.MESSAGE_LOGO_UPLOAD_URL
        )


class LogoView(APIView):
    def put(self, request, workspace_id):
        data = ConfirmLogoSerializer.parse(request.data)
        logo_service.confirm_logo(request.user, workspace_id, data["key"])
        membership = access.get_membership(request.user, workspace_id)
        return SuccessResponse(
            data=WorkspaceData(membership), message=messages.MESSAGE_LOGO_UPDATED
        )

    def delete(self, request, workspace_id):
        logo_service.remove_logo(request.user, workspace_id)
        return ResourceDeletedResponse(
            data=DictData({}), message=messages.MESSAGE_LOGO_REMOVED
        )
