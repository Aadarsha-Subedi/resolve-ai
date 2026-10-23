from rest_framework.views import APIView

from common.pagination.domain import OffsetBasedPagination
from common.response.domain import (
    ListResponseData,
    ResourceDeletedResponse,
    ResourceListResponse,
    SuccessResponse,
)
from common.throttling.scoped import AuthScopedThrottle, UserThrottle
from knowledge.constants import messages
from knowledge.serializers.requests import (
    AskQuestionSerializer,
    ContextQuestionSerializer,
)
from knowledge.serializers.responses import (
    AnswerData,
    ContextData,
    ConversationData,
    DictData,
    answer_payload,
)
from knowledge.services import answer_service, ask_history, context_service


class ContextView(APIView):
    """POST {"query": "..."}: passages of published articles and uploaded documents that
    answer a question typed into the chat box, with citations. Uses the caller's AI settings
    for query rewriting, and the Resolve AI key to embed the query for the search by meaning."""

    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "ai"

    def post(self, request, workspace_id):
        data = ContextQuestionSerializer.parse(request.data)
        result = context_service.retrieve_for_question(
            request.user, workspace_id, data["query"]
        )
        return SuccessResponse(
            data=ContextData(result), message=messages.MESSAGE_CONTEXT_FOUND
        )


class AskView(APIView):
    """POST {"query", "conversation_id"?}: the same passages as `context/`, plus an answer the
    LLM paraphrases from them with [n] citations. The exchange is stored in the caller's chat
    history (a new conversation unless `conversation_id` names one of theirs). Costs up to two
    LLM calls (rewrite, answer)."""

    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "ai"

    def post(self, request, workspace_id):
        data = AskQuestionSerializer.parse(request.data)
        result = answer_service.answer_question(
            request.user,
            workspace_id,
            data["query"],
            data.get("conversation_id"),
            to_dict=answer_payload,
        )
        return SuccessResponse(
            data=AnswerData(result), message=messages.MESSAGE_ANSWER_FOUND
        )


class AskConversationListView(APIView):
    def get(self, request, workspace_id):
        paginator = OffsetBasedPagination()
        page = paginator.paginate_queryset(
            ask_history.list_conversations(request.user, workspace_id), request
        )
        return ResourceListResponse(
            data=ListResponseData(items=[ConversationData(c) for c in page]),
            meta=paginator.get_meta(),
            message=messages.MESSAGE_CONVERSATIONS_LISTED,
        )


class AskConversationDetailView(APIView):
    def get(self, request, workspace_id, conversation_id):
        conversation = ask_history.get_conversation(
            request.user, workspace_id, conversation_id
        )
        return SuccessResponse(
            data=ConversationData(conversation, with_turns=True),
            message=messages.MESSAGE_CONVERSATION_RETRIEVED,
        )

    def delete(self, request, workspace_id, conversation_id):
        ask_history.delete_conversation(request.user, workspace_id, conversation_id)
        return ResourceDeletedResponse(
            data=DictData({}), message=messages.MESSAGE_CONVERSATION_DELETED
        )
