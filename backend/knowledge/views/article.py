from rest_framework.views import APIView

from common.pagination.domain import OffsetBasedPagination
from common.response.domain import (
    ListResponseData,
    ResourceCreatedResponse,
    ResourceDeletedResponse,
    ResourceListResponse,
    ResourceUpdatedResponse,
    SuccessResponse,
)
from knowledge.constants import messages
from knowledge.constants.enums import ArticleStatus
from knowledge.serializers.requests import (
    ArticleFilterSerializer,
    CreateArticleSerializer,
    UpdateArticleSerializer,
)
from knowledge.serializers.responses import ArticleData, DictData
from knowledge.services import article_service
from workspaces.constants import permissions
from workspaces.services import access


class ArticleListView(APIView):
    """GET filters: ?title=&status=&category=<id>&ordering=-updated_at (plus limit/offset)."""

    def get(self, request, workspace_id):
        filters = ArticleFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        queryset = article_service.list_articles(
            request.user, workspace_id, **filters.validated_data
        )
        paginator = OffsetBasedPagination()
        page = paginator.paginate_queryset(queryset, request)
        return ResourceListResponse(
            data=ListResponseData(items=[ArticleData(a) for a in page]),
            meta=paginator.get_meta(),
            message=messages.MESSAGE_ARTICLES_LISTED,
        )

    def post(self, request, workspace_id):
        data = CreateArticleSerializer.parse(request.data)
        article = article_service.create_article(
            request.user,
            workspace_id,
            data["title"],
            data["content"],
            data["category_ids"],
        )
        return ResourceCreatedResponse(
            data=ArticleData(article, content=data["content"]),
            message=messages.MESSAGE_ARTICLE_CREATED,
        )


class ArticleDetailView(APIView):
    def get(self, request, workspace_id, article_id):
        access.require_permission(
            request.user, workspace_id, permissions.KNOWLEDGE_VIEW
        )
        article = article_service.get_article(workspace_id, article_id)
        return SuccessResponse(
            data=ArticleData(article, content=article.content),
            message=messages.MESSAGE_ARTICLE_RETRIEVED,
        )

    def patch(self, request, workspace_id, article_id):
        data = UpdateArticleSerializer.parse(request.data)
        article = article_service.update_article(
            request.user,
            workspace_id,
            article_id,
            data.get("title"),
            data.get("content"),
            data.get("category_ids"),
        )
        return ResourceUpdatedResponse(
            data=ArticleData(article, content=article.content),
            message=messages.MESSAGE_ARTICLE_UPDATED,
        )

    def delete(self, request, workspace_id, article_id):
        article_service.delete_article(request.user, workspace_id, article_id)
        return ResourceDeletedResponse(
            data=DictData({}), message=messages.MESSAGE_ARTICLE_DELETED
        )


class _StatusView(APIView):
    target: str
    message: str

    def post(self, request, workspace_id, article_id):
        article = article_service.change_status(
            request.user, workspace_id, article_id, self.target
        )
        return SuccessResponse(data=ArticleData(article), message=self.message)


class PublishArticleView(_StatusView):
    target = ArticleStatus.PUBLISHED
    message = messages.MESSAGE_ARTICLE_PUBLISHED


class UnpublishArticleView(_StatusView):
    target = ArticleStatus.DRAFT
    message = messages.MESSAGE_ARTICLE_UNPUBLISHED


class ArchiveArticleView(_StatusView):
    target = ArticleStatus.ARCHIVED
    message = messages.MESSAGE_ARTICLE_ARCHIVED
