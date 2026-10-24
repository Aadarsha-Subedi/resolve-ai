from django.conf import settings
from rest_framework.views import APIView

from common.response.domain import (
    ListResponseData,
    ResourceCreatedResponse,
    ResourceListResponse,
    ResourceUpdatedResponse,
    SuccessResponse,
)
from workspaces.constants import messages
from workspaces.serializers.requests import (
    CreateWorkspaceSerializer,
    TransferOwnershipSerializer,
    UpdateWorkspaceSerializer,
)
from workspaces.serializers.responses import DictData, WorkspaceData
from workspaces.services import (
    access,
    demo_service,
    member_service,
    workspace_service,
)
from workspaces.views.common import paginate


class WorkspaceListView(APIView):
    """GET /api/workspaces/ (mine), POST /api/workspaces/ (create; caller becomes owner)."""

    def get(self, request):
        page, meta = paginate(request, workspace_service.list_workspaces(request.user))
        return ResourceListResponse(
            data=ListResponseData(items=[WorkspaceData(m) for m in page]),
            meta=meta,
            message=messages.MESSAGE_WORKSPACES_LISTED,
        )

    def post(self, request):
        data = CreateWorkspaceSerializer.parse(request.data)
        workspace = workspace_service.create_workspace(
            request.user, data["name"], data.get("slug")
        )
        membership = access.get_membership(request.user, workspace.id)
        return ResourceCreatedResponse(
            data=WorkspaceData(membership), message=messages.MESSAGE_WORKSPACE_CREATED
        )


class WorkspaceDetailView(APIView):
    def get(self, request, workspace_id):
        membership = access.get_membership(request.user, workspace_id)
        return SuccessResponse(
            data=WorkspaceData(membership), message=messages.MESSAGE_WORKSPACE_RETRIEVED
        )

    def patch(self, request, workspace_id):
        data = UpdateWorkspaceSerializer.parse(request.data)
        membership = workspace_service.update_workspace(
            request.user,
            workspace_id,
            data.get("name"),
            data.get("portal_enabled"),
            data.get("search_language"),
        )
        return ResourceUpdatedResponse(
            data=WorkspaceData(membership), message=messages.MESSAGE_WORKSPACE_UPDATED
        )

    def delete(self, request, workspace_id):
        workspace_service.delete_workspace(request.user, workspace_id)
        return SuccessResponse(
            data=DictData({}),
            message=messages.MESSAGE_WORKSPACE_DELETED.format(
                days=settings.WORKSPACE_DELETION_GRACE_DAYS
            ),
        )


class DemoWorkspaceView(APIView):
    """POST /api/workspaces/demo/: open your demo workspace, creating it if you have none
    (201 when created, 200 with the existing one)."""

    def post(self, request):
        membership, created = demo_service.explore_demo(request.user)
        if created:
            return ResourceCreatedResponse(
                data=WorkspaceData(membership), message=messages.MESSAGE_DEMO_CREATED
            )
        return SuccessResponse(
            data=WorkspaceData(membership), message=messages.MESSAGE_DEMO_EXISTS
        )


class DemoResetView(APIView):
    """POST /api/workspaces/{id}/demo/reset/: owner only, demo workspaces only."""

    def post(self, request, workspace_id):
        membership = demo_service.reset_demo(request.user, workspace_id)
        return SuccessResponse(
            data=WorkspaceData(membership), message=messages.MESSAGE_DEMO_RESET
        )


class TransferOwnershipView(APIView):
    def post(self, request, workspace_id):
        data = TransferOwnershipSerializer.parse(request.data)
        member_service.transfer_ownership(request.user, workspace_id, data["user_id"])
        membership = access.get_membership(request.user, workspace_id)
        return SuccessResponse(
            data=WorkspaceData(membership),
            message=messages.MESSAGE_OWNERSHIP_TRANSFERRED,
        )
