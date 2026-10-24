import logging

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.exception.domain import ConflictException
from common.pagination.domain import OffsetBasedPagination
from common.response.domain import (
    ListResponseData,
    ResourceDeletedResponse,
    ResourceListResponse,
    SuccessResponse,
)
from common.throttling.scoped import (
    AnonThrottle,
    AuthScopedThrottle,
    IPScopedThrottle,
    UserThrottle,
)
from email_integration.constants import errors, messages
from email_integration.serializers.requests import AttachReviewSerializer
from email_integration.serializers.responses import (
    ConnectionData,
    DictData,
    ReviewItemData,
)
from email_integration.services import (
    connection_service,
    inbound_service,
    push_service,
    review_service,
    send_service,
)
from email_integration.tasks import sync_mailbox
from tickets.serializers.responses import MessageData

logger = logging.getLogger(__name__)


class GmailStatusView(APIView):
    """GET status of my Gmail connection; DELETE disconnect (revokes at Google)."""

    def get(self, request):
        return SuccessResponse(
            data=ConnectionData(connection_service.get_connection(request.user)),
            message=messages.MESSAGE_STATUS_RETRIEVED,
        )

    def delete(self, request):
        connection_service.disconnect(request.user)
        return ResourceDeletedResponse(
            data=DictData({}), message=messages.MESSAGE_DISCONNECTED
        )


class GmailSyncView(APIView):
    """POST: "Sync latest mails". Reads at most the newest GMAIL_MANUAL_SYNC_LIMIT messages."""

    throttle_classes = [UserThrottle, AuthScopedThrottle]
    throttle_scope = "gmail_sync"

    def post(self, request):
        connection = connection_service.get_connection(request.user)
        if connection is None or not connection.is_connected:
            raise ConflictException(
                messages.MESSAGE_NOT_CONNECTED, error_code=errors.ERROR_NOT_CONNECTED
            )
        report = inbound_service.manual_sync(connection)
        if report.reauth_required:
            raise ConflictException(
                messages.MESSAGE_REAUTH_REQUIRED,
                error_code=errors.ERROR_REAUTH_REQUIRED,
            )
        return SuccessResponse(
            data=DictData(
                {
                    "matched": report.matched,
                    "needs_review": report.review,
                    "duplicates": report.duplicate,
                    "ignored": report.ignored,
                    "limit": settings.GMAIL_MANUAL_SYNC_LIMIT,
                }
            ),
            message=messages.MESSAGE_SYNCED,
        )


class GmailPushView(APIView):
    """POST from Google Pub/Sub (signed JWT, no session). Always answers 2xx once the
    caller is authenticated so Pub/Sub does not redeliver forever."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonThrottle, IPScopedThrottle]
    throttle_scope = "webhook"

    def post(self, request):
        push_service.verify_request(request.headers.get("Authorization", ""))
        decoded = push_service.decode_notification(
            request.data if isinstance(request.data, dict) else {}
        )
        if decoded is not None:
            mailbox_email, _history_id = decoded
            for connection in connection_service.GmailConnection.objects.filter(
                mailbox_email__iexact=mailbox_email
            ):
                if connection.is_connected:
                    sync_mailbox.delay(str(connection.id))
        return SuccessResponse(
            data=DictData({}), message=messages.MESSAGE_PUSH_ACCEPTED
        )


class ReviewListView(APIView):
    def get(self, request):
        paginator = OffsetBasedPagination()
        page = paginator.paginate_queryset(
            review_service.list_review(request.user), request
        )
        return ResourceListResponse(
            data=ListResponseData(items=[ReviewItemData(i) for i in page]),
            meta=paginator.get_meta(),
            message=messages.MESSAGE_REVIEW_LISTED,
        )


class ReviewAttachView(APIView):
    def post(self, request, review_id):
        data = AttachReviewSerializer.parse(request.data)
        review_service.attach_to_ticket(
            request.user, review_id, data["workspace_id"], data["ticket_id"]
        )
        return SuccessResponse(
            data=DictData({}), message=messages.MESSAGE_REVIEW_ATTACHED
        )


class ReviewDismissView(APIView):
    def post(self, request, review_id):
        review_service.dismiss(request.user, review_id)
        return SuccessResponse(
            data=DictData({}), message=messages.MESSAGE_REVIEW_DISMISSED
        )


class ResendMessageView(APIView):
    """POST: put a failed public reply back in the queue."""

    def post(self, request, workspace_id, ticket_id, message_id):
        from email_integration.tasks import send_ticket_message

        message = send_service.resend(request.user, workspace_id, ticket_id, message_id)
        send_ticket_message.delay(str(message.id))
        message.refresh_from_db()
        return SuccessResponse(
            data=MessageData(message), message=messages.MESSAGE_RESEND_QUEUED
        )
