from rest_framework.views import APIView

from audit.constants import messages
from audit.constants.dashboard import THROTTLE_SCOPE
from audit.serializers.dashboard_requests import DashboardQuerySerializer
from audit.serializers.dashboard_responses import DashboardData
from audit.services import dashboard_service
from common.response.domain import SuccessResponse
from common.throttling.scoped import (
    AuthScopedThrottle,
    UserThrottle,
    WorkspaceThrottle,
)


class DashboardView(APIView):
    """GET /api/workspaces/{id}/dashboard/: everything the dashboard screen shows.

    Query: period (7d, 30d, 90d; default 30d) or from and to (dates, at most 366 days),
    tz (IANA name, default UTC), include (comma list of summary, volume, recent_tickets,
    waiting, activity), recent_limit, waiting_limit, activity_limit (1 to 50)."""

    http_method_names = ["get", "head", "options"]
    throttle_classes = [UserThrottle, WorkspaceThrottle, AuthScopedThrottle]
    throttle_scope = THROTTLE_SCOPE

    def get(self, request, workspace_id):
        query = DashboardQuerySerializer.parse(request.query_params)
        result = dashboard_service.get_dashboard(request.user, workspace_id, query)
        return SuccessResponse(
            data=DashboardData(result.data),
            meta={"cached": result.cached},
            message=messages.MESSAGE_DASHBOARD_RETRIEVED,
        )
