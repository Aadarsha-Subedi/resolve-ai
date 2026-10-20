from rest_framework.views import APIView

from common.response.domain import (
    ListResponseData,
    ResourceDeletedResponse,
    ResourceListResponse,
    SuccessResponse,
)
from workspaces.constants import messages
from workspaces.serializers.responses import DictData, MemberData
from workspaces.services import member_service
from workspaces.views.common import paginate


class MemberListView(APIView):
    def get(self, request, workspace_id):
        page, meta = paginate(
            request, member_service.list_members(request.user, workspace_id)
        )
        return ResourceListResponse(
            data=ListResponseData(items=[MemberData(m) for m in page]),
            meta=meta,
            message=messages.MESSAGE_MEMBERS_LISTED,
        )


class MemberDetailView(APIView):
    def delete(self, request, workspace_id, user_id):
        member_service.remove_member(request.user, workspace_id, user_id)
        return ResourceDeletedResponse(
            data=DictData({}), message=messages.MESSAGE_MEMBER_REMOVED
        )


class LeaveWorkspaceView(APIView):
    def post(self, request, workspace_id):
        member_service.leave_workspace(request.user, workspace_id)
        return SuccessResponse(
            data=DictData({}), message=messages.MESSAGE_LEFT_WORKSPACE
        )
