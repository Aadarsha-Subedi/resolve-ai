from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.response.domain import ResourceCreatedResponse, SuccessResponse
from common.throttling.scoped import AnonThrottle, IPScopedThrottle
from tickets.constants import messages
from tickets.constants.settings import PORTAL_HONEYPOT_FIELD
from tickets.serializers.requests import PortalTicketSerializer
from tickets.serializers.responses import DictData
from tickets.services import portal_service


class _PortalView(APIView):
    """Public, no login: no session authentication (so no CSRF cookie is needed)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]


class PortalInfoView(_PortalView):
    throttle_classes = [AnonThrottle]

    def get(self, request, slug):
        workspace = portal_service.get_portal_workspace(slug)
        return SuccessResponse(
            data=DictData(portal_service.portal_info(workspace)),
            message=messages.MESSAGE_PORTAL_RETRIEVED,
        )


class PortalTicketView(_PortalView):
    """POST /api/portal/{slug}/tickets/: limited per IP (scope portal_ticket)."""

    throttle_classes = [AnonThrottle, IPScopedThrottle]
    throttle_scope = "portal_ticket"

    def post(self, request, slug):
        serializer = PortalTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        honeypot = bool(str(request.data.get(PORTAL_HONEYPOT_FIELD, "")).strip())
        number = portal_service.submit(slug, serializer.validated_data, honeypot)
        return ResourceCreatedResponse(
            data=DictData({"number": number}),
            message=messages.MESSAGE_PORTAL_SUBMITTED.format(number=number),
        )
