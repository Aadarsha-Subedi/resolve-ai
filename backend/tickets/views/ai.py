from rest_framework.views import APIView

from common.response.domain import SuccessResponse
from common.throttling.scoped import AuthScopedThrottle, UserThrottle
from knowledge.serializers.responses import DictData
from tickets.constants import messages
from tickets.serializers.requests import DraftReplySerializer
from tickets.services import ai_service


class TicketSummaryView(APIView):
    """POST: a short AI summary of the ticket's public conversation. Nothing is stored."""

    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "ai"

    def post(self, request, workspace_id, ticket_id):
        summary = ai_service.summarize(request.user, workspace_id, ticket_id)
        return SuccessResponse(
            data=DictData({"summary": summary}), message=messages.MESSAGE_SUMMARY_READY
        )


class TicketDraftReplyView(APIView):
    """POST {"intent": "..."}: a draft reply to the customer for the agent to edit. Uses the
    public conversation, matching knowledge-base passages and the agent's instruction."""

    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "ai"

    def post(self, request, workspace_id, ticket_id):
        data = DraftReplySerializer.parse(request.data)
        result = ai_service.draft_reply(
            request.user, workspace_id, ticket_id, data["intent"]
        )
        return SuccessResponse(
            data=DictData(
                {
                    "draft": result.draft,
                    "sources": [
                        {
                            "article_id": s.article_id,
                            "title": s.title,
                            "section": s.section,
                        }
                        for s in result.sources
                    ],
                }
            ),
            message=messages.MESSAGE_DRAFT_READY,
        )
