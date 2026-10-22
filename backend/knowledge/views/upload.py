from rest_framework.views import APIView

from common.pagination.domain import OffsetBasedPagination
from common.response.domain import (
    ListResponseData,
    ResourceCreatedResponse,
    ResourceDeletedResponse,
    ResourceListResponse,
    SuccessResponse,
)
from knowledge.constants import messages
from knowledge.serializers.requests import UploadFilterSerializer, UploadUrlSerializer
from knowledge.serializers.responses import DictData, UploadData
from knowledge.services import quota_service, upload_service
from workspaces.constants import permissions
from workspaces.services import access


class UploadListView(APIView):
    """GET filters: category (id), filename (contains)."""

    def get(self, request, workspace_id):
        filters = UploadFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        paginator = OffsetBasedPagination()
        page = paginator.paginate_queryset(
            upload_service.list_uploads(
                request.user, workspace_id, **filters.validated_data
            ),
            request,
        )
        return ResourceListResponse(
            data=ListResponseData(items=[UploadData(u) for u in page]),
            meta=paginator.get_meta(),
            message=messages.MESSAGE_UPLOADS_LISTED,
        )


class UploadUrlView(APIView):
    """POST: reserve space and get a signed PUT URL (PDF or TXT, up to 10 MB)."""

    def post(self, request, workspace_id):
        data = UploadUrlSerializer.parse(request.data)
        upload, signed = upload_service.create_upload(
            request.user,
            workspace_id,
            data["filename"],
            data["content_type"],
            data["size"],
            data["category_id"],
        )
        return ResourceCreatedResponse(
            data=UploadData(upload, extra=signed), message=messages.MESSAGE_UPLOAD_URL
        )


class UploadConfirmView(APIView):
    def post(self, request, workspace_id, upload_id):
        upload = upload_service.confirm_upload(request.user, workspace_id, upload_id)
        return SuccessResponse(
            data=UploadData(upload), message=messages.MESSAGE_UPLOAD_CONFIRMED
        )


class UploadDetailView(APIView):
    def delete(self, request, workspace_id, upload_id):
        upload_service.delete_upload(request.user, workspace_id, upload_id)
        return ResourceDeletedResponse(
            data=DictData({}), message=messages.MESSAGE_UPLOAD_DELETED
        )


class UploadDownloadView(APIView):
    def get(self, request, workspace_id, upload_id):
        payload = upload_service.download_url(request.user, workspace_id, upload_id)
        return SuccessResponse(
            data=DictData(payload), message=messages.MESSAGE_DOWNLOAD_URL
        )


class StorageUsageView(APIView):
    def get(self, request, workspace_id):
        access.require_permission(
            request.user, workspace_id, permissions.KNOWLEDGE_VIEW
        )
        return SuccessResponse(
            data=DictData(quota_service.usage(workspace_id)),
            message=messages.MESSAGE_STORAGE_RETRIEVED,
        )
