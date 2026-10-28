from rest_framework.views import APIView

from ai.constants import messages
from ai.serializers.requests import UsageFilterSerializer
from ai.serializers.responses import UsageLogData
from ai.services import usage_service
from common.pagination.domain import OffsetBasedPagination
from common.response.domain import ListResponseData, ResourceListResponse
from common.throttling.scoped import AuthScopedThrottle, UserThrottle


class UsageLogListView(APIView):
    """GET /api/workspaces/{id}/ai/usage/: the workspace's AI usage log, owner only.

    Query: search (question, answer, user), feature, outcome, actor (user id), created_from,
    created_to, ordering (created_at, user, feature, outcome, tokens; prefix `-` for
    descending, default `-created_at`), limit/offset (25, max 100). `meta.summary` counts
    the filtered rows. Read-only."""

    http_method_names = ["get", "head", "options"]
    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "ai_usage"

    def get(self, request, workspace_id):
        filters = UsageFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        queryset = usage_service.list_logs(
            request.user, workspace_id, **filters.validated_data
        )
        paginator = OffsetBasedPagination()
        page = paginator.paginate_queryset(queryset, request)
        return ResourceListResponse(
            data=ListResponseData(items=[UsageLogData(row) for row in page]),
            meta={**paginator.get_meta(), "summary": usage_service.summary(queryset)},
            message=messages.MESSAGE_USAGE_LISTED,
        )
