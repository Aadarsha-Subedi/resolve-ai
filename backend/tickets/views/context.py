from rest_framework.views import APIView

from common.response.domain import SuccessResponse
from common.throttling.scoped import AuthScopedThrottle, UserThrottle
from knowledge.constants import messages as knowledge_messages
from knowledge.serializers.responses import ContextData
from tickets.serializers.requests import TicketContextSerializer
from tickets.services import context_service


class TicketContextView(APIView):
    """POST {"message_id": "..."} (optional): passages of published articles relevant to the
    ticket, or to one public customer message of it. Internal notes are never used."""

    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "ai"

    def post(self, request, workspace_id, ticket_id):
        data = TicketContextSerializer.parse(request.data)
        result = context_service.ticket_context(
            request.user, workspace_id, ticket_id, data.get("message_id")
        )
        return SuccessResponse(
            data=ContextData(result), message=knowledge_messages.MESSAGE_CONTEXT_FOUND
        )
