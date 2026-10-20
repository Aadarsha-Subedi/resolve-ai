from rest_framework.views import APIView

from common.pagination.domain import OffsetBasedPagination
from common.response.domain import (
    ListResponseData,
    ResourceCreatedResponse,
    ResourceListResponse,
    ResourceUpdatedResponse,
    SuccessResponse,
)
from tickets.constants import messages
from tickets.serializers.requests import (
    AddMessageSerializer,
    ChangeStatusSerializer,
    CreateTicketSerializer,
    OverviewQuerySerializer,
    TicketFilterSerializer,
    UpdateTicketSerializer,
)
from tickets.serializers.responses import (
    EventData,
    MessageData,
    OverviewData,
    TicketData,
)
from tickets.services import message_service, overview_service, ticket_service


def _paged(request, queryset):
    paginator = OffsetBasedPagination()
    return paginator.paginate_queryset(queryset, request), paginator.get_meta()


class TicketListView(APIView):
    """GET filters: status, priority, category, created_from, created_to (dates), q
    (contains in subject/email/name), waiting_for_reply, ordering."""

    def get(self, request, workspace_id):
        # partial: a missing query parameter must not become False (DRF's HTML-input default)
        filters = TicketFilterSerializer(data=request.query_params, partial=True)
        filters.is_valid(raise_exception=True)
        queryset = ticket_service.list_tickets(
            request.user, workspace_id, **filters.validated_data
        )
        page, meta = _paged(request, queryset)
        return ResourceListResponse(
            data=ListResponseData(items=[TicketData(t) for t in page]),
            meta=meta,
            message=messages.MESSAGE_TICKETS_LISTED,
        )

    def post(self, request, workspace_id):
        data = CreateTicketSerializer.parse(request.data)
        ticket = ticket_service.create_by_agent(request.user, workspace_id, data)
        return ResourceCreatedResponse(
            data=TicketData(ticket, detail=True),
            message=messages.MESSAGE_TICKET_CREATED,
        )


class TicketDetailView(APIView):
    def get(self, request, workspace_id, ticket_id):
        ticket = ticket_service.get_for_user(request.user, workspace_id, ticket_id)
        return SuccessResponse(
            data=TicketData(ticket, detail=True),
            message=messages.MESSAGE_TICKET_RETRIEVED,
        )

    def patch(self, request, workspace_id, ticket_id):
        data = UpdateTicketSerializer.parse(request.data)
        ticket = ticket_service.update_ticket(
            request.user, workspace_id, ticket_id, data
        )
        return ResourceUpdatedResponse(
            data=TicketData(ticket, detail=True),
            message=messages.MESSAGE_TICKET_UPDATED,
        )


class TicketOverviewView(APIView):
    """GET: everything the ticket page needs in one call (replaces separate calls for the
    ticket, its messages, its history, the viewer's role and their Gmail status).
    ?messages_limit= and ?events_limit= (1-100, default 50) return the newest items; older
    ones come from the paginated messages/ and events/ endpoints."""

    def get(self, request, workspace_id, ticket_id):
        query = OverviewQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        overview = overview_service.build(
            request.user, workspace_id, ticket_id, **query.validated_data
        )
        return SuccessResponse(
            data=OverviewData(overview), message=messages.MESSAGE_OVERVIEW_RETRIEVED
        )


class TicketStatusView(APIView):
    def post(self, request, workspace_id, ticket_id):
        data = ChangeStatusSerializer.parse(request.data)
        ticket = ticket_service.change_status(
            request.user, workspace_id, ticket_id, data["status"]
        )
        return SuccessResponse(
            data=TicketData(ticket, detail=True),
            message=messages.MESSAGE_STATUS_CHANGED,
        )


class TicketMessageListView(APIView):
    def get(self, request, workspace_id, ticket_id):
        page, meta = _paged(
            request,
            message_service.list_messages(request.user, workspace_id, ticket_id),
        )
        return ResourceListResponse(
            data=ListResponseData(items=[MessageData(m) for m in page]),
            meta=meta,
            message=messages.MESSAGE_MESSAGES_LISTED,
        )

    def post(self, request, workspace_id, ticket_id):
        data = AddMessageSerializer.parse(request.data)
        message = message_service.add_message(
            request.user, workspace_id, ticket_id, data["body"], data["visibility"]
        )
        return ResourceCreatedResponse(
            data=MessageData(message),
            message=(
                messages.MESSAGE_REPLY_ADDED
                if data["visibility"] == "public"
                else messages.MESSAGE_NOTE_ADDED
            ),
        )


class TicketEventListView(APIView):
    def get(self, request, workspace_id, ticket_id):
        page, meta = _paged(
            request, ticket_service.list_events(request.user, workspace_id, ticket_id)
        )
        return ResourceListResponse(
            data=ListResponseData(items=[EventData(e) for e in page]),
            meta=meta,
            message=messages.MESSAGE_EVENTS_LISTED,
        )
