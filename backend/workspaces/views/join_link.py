from rest_framework.views import APIView

from common.response.domain import (
    ResourceCreatedResponse,
    ResourceDeletedResponse,
    SuccessResponse,
)
from common.throttling.scoped import IPScopedThrottle, UserThrottle
from workspaces.constants import messages
from workspaces.serializers.requests import (
    RedeemJoinLinkSerializer,
    RotateJoinLinkSerializer,
)
from workspaces.serializers.responses import (
    DictData,
    IssuedJoinLinkData,
    JoinLinkData,
    WorkspaceData,
)
from workspaces.services import join_link_service


class JoinLinkView(APIView):
    """GET status, POST create/rotate, DELETE revoke (owner only)."""

    def get(self, request, workspace_id):
        link = join_link_service.current_link(request.user, workspace_id)
        return SuccessResponse(
            data=JoinLinkData(link), message=messages.MESSAGE_JOIN_LINK_RETRIEVED
        )

    def post(self, request, workspace_id):
        data = RotateJoinLinkSerializer.parse(request.data)
        issued = join_link_service.rotate_link(
            request.user, workspace_id, data["expires_in"]
        )
        return ResourceCreatedResponse(
            data=IssuedJoinLinkData(issued), message=messages.MESSAGE_JOIN_LINK_CREATED
        )

    def delete(self, request, workspace_id):
        join_link_service.revoke_link(request.user, workspace_id)
        return ResourceDeletedResponse(
            data=DictData({}), message=messages.MESSAGE_JOIN_LINK_REVOKED
        )


class RedeemJoinLinkView(APIView):
    """POST /api/join-links/redeem/: join with a raw token. Limited per IP (scope join_link)."""

    throttle_classes = [UserThrottle, IPScopedThrottle]
    throttle_scope = "join_link"

    def post(self, request):
        data = RedeemJoinLinkSerializer.parse(request.data)
        membership, joined = join_link_service.redeem(request.user, data["token"])
        return SuccessResponse(
            data=WorkspaceData(membership),
            message=(
                messages.MESSAGE_JOINED if joined else messages.MESSAGE_ALREADY_MEMBER
            ),
            meta={"joined": joined},
        )
