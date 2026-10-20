from rest_framework.views import APIView

from audit.constants import messages
from audit.serializers.requests import AuditFilterSerializer
from audit.serializers.responses import AuditEventData
from audit.services import list_service
from common.pagination.domain import OffsetBasedPagination
from common.response.domain import ListResponseData, ResourceListResponse


class AuditEventListView(APIView):
    """GET /api/workspaces/{id}/audit/: the workspace's audit log, owner only, newest first.

    Filters: action, action_prefix (for example `member.`), actor (user id), target_type,
    target_id, created_from, created_to; plus limit/offset (25, max 100). Read-only: there is
    no create, change, delete or export endpoint."""

    http_method_names = ["get", "head", "options"]

    def get(self, request, workspace_id):
        filters = AuditFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        queryset = list_service.list_events(
            request.user, workspace_id, **filters.validated_data
        )
        paginator = OffsetBasedPagination()
        page = paginator.paginate_queryset(queryset, request)
        return ResourceListResponse(
            data=ListResponseData(items=[AuditEventData(e) for e in page]),
            meta=paginator.get_meta(),
            message=messages.MESSAGE_AUDIT_LISTED,
        )
