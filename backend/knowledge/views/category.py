from rest_framework.views import APIView

from common.pagination.domain import OffsetBasedPagination
from common.response.domain import (
    ListResponseData,
    ResourceCreatedResponse,
    ResourceDeletedResponse,
    ResourceListResponse,
    ResourceUpdatedResponse,
)
from knowledge.constants import messages
from knowledge.serializers.requests import CategorySerializer
from knowledge.serializers.responses import CategoryData, DictData
from knowledge.services import category_service


class CategoryListView(APIView):
    def get(self, request, workspace_id):
        paginator = OffsetBasedPagination()
        page = paginator.paginate_queryset(
            category_service.list_categories(request.user, workspace_id), request
        )
        return ResourceListResponse(
            data=ListResponseData(items=[CategoryData(c) for c in page]),
            meta=paginator.get_meta(),
            message=messages.MESSAGE_CATEGORIES_LISTED,
        )

    def post(self, request, workspace_id):
        data = CategorySerializer.parse(request.data)
        category = category_service.create_category(
            request.user, workspace_id, data["name"]
        )
        return ResourceCreatedResponse(
            data=CategoryData(category), message=messages.MESSAGE_CATEGORY_CREATED
        )


class CategoryDetailView(APIView):
    def patch(self, request, workspace_id, category_id):
        data = CategorySerializer.parse(request.data)
        category = category_service.rename_category(
            request.user, workspace_id, category_id, data["name"]
        )
        return ResourceUpdatedResponse(
            data=CategoryData(category), message=messages.MESSAGE_CATEGORY_UPDATED
        )

    def delete(self, request, workspace_id, category_id):
        category_service.delete_category(request.user, workspace_id, category_id)
        return ResourceDeletedResponse(
            data=DictData({}), message=messages.MESSAGE_CATEGORY_DELETED
        )
