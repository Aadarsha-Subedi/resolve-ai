from rest_framework.views import APIView

from common.response.domain import (
    ListResponseData,
    ResourceCreatedResponse,
    ResourceDeletedResponse,
    ResourceListResponse,
    SuccessResponse,
)
from workspaces.constants import messages
from workspaces.serializers.requests import CreateInvitationsSerializer
from workspaces.serializers.responses import (
    DictData,
    InvitationData,
    InvitationOutcomeData,
    MyInvitationData,
    WorkspaceData,
)
from workspaces.services import invitation_service
from workspaces.views.common import paginate


class WorkspaceInvitationListView(APIView):
    """Owner: list open invitations / invite one or several Google accounts."""

    def get(self, request, workspace_id):
        page, meta = paginate(
            request,
            invitation_service.list_workspace_invitations(request.user, workspace_id),
        )
        return ResourceListResponse(
            data=ListResponseData(items=[InvitationData(i) for i in page]),
            meta=meta,
            message=messages.MESSAGE_INVITATIONS_LISTED,
        )

    def post(self, request, workspace_id):
        data = CreateInvitationsSerializer.parse(request.data)
        results = invitation_service.create_invitations(
            request.user, workspace_id, data["emails"]
        )
        return ResourceCreatedResponse(
            data=ListResponseData(
                items=[
                    InvitationOutcomeData(r.email, r.outcome, r.invitation)
                    for r in results
                ]
            ),
            message=messages.MESSAGE_INVITATIONS_CREATED,
        )


class WorkspaceInvitationDetailView(APIView):
    def delete(self, request, workspace_id, invitation_id):
        invitation_service.revoke_invitation(request.user, workspace_id, invitation_id)
        return ResourceDeletedResponse(
            data=DictData({}), message=messages.MESSAGE_INVITATION_REVOKED
        )


class MyInvitationListView(APIView):
    """Open invitations for the signed-in Google mailbox."""

    def get(self, request):
        page, meta = paginate(
            request, invitation_service.list_my_invitations(request.user)
        )
        return ResourceListResponse(
            data=ListResponseData(items=[MyInvitationData(i) for i in page]),
            meta=meta,
            message=messages.MESSAGE_INVITATIONS_LISTED,
        )


class AcceptInvitationView(APIView):
    def post(self, request, invitation_id):
        membership = invitation_service.accept_invitation(request.user, invitation_id)
        return SuccessResponse(
            data=WorkspaceData(membership), message=messages.MESSAGE_INVITATION_ACCEPTED
        )


class DeclineInvitationView(APIView):
    def post(self, request, invitation_id):
        invitation_service.decline_invitation(request.user, invitation_id)
        return SuccessResponse(
            data=DictData({}), message=messages.MESSAGE_INVITATION_DECLINED
        )
