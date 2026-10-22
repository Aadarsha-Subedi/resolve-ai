from django.urls import path

from knowledge.views import article, category, context, upload

_W = "workspaces/<uuid:workspace_id>/knowledge/"

urlpatterns = [
    path(_W + "articles/", article.ArticleListView.as_view(), name="article_list"),
    path(
        _W + "articles/<uuid:article_id>/",
        article.ArticleDetailView.as_view(),
        name="article_detail",
    ),
    path(
        _W + "articles/<uuid:article_id>/publish/",
        article.PublishArticleView.as_view(),
        name="article_publish",
    ),
    path(
        _W + "articles/<uuid:article_id>/unpublish/",
        article.UnpublishArticleView.as_view(),
        name="article_unpublish",
    ),
    path(
        _W + "articles/<uuid:article_id>/archive/",
        article.ArchiveArticleView.as_view(),
        name="article_archive",
    ),
    path(_W + "categories/", category.CategoryListView.as_view(), name="category_list"),
    path(
        _W + "categories/<uuid:category_id>/",
        category.CategoryDetailView.as_view(),
        name="category_detail",
    ),
    path(_W + "uploads/", upload.UploadListView.as_view(), name="upload_list"),
    path(_W + "uploads/upload-url/", upload.UploadUrlView.as_view(), name="upload_url"),
    path(
        _W + "uploads/<uuid:upload_id>/confirm/",
        upload.UploadConfirmView.as_view(),
        name="upload_confirm",
    ),
    path(
        _W + "uploads/<uuid:upload_id>/download/",
        upload.UploadDownloadView.as_view(),
        name="upload_download",
    ),
    path(
        _W + "uploads/<uuid:upload_id>/",
        upload.UploadDetailView.as_view(),
        name="upload_detail",
    ),
    path(_W + "context/", context.ContextView.as_view(), name="knowledge_context"),
    path(_W + "ask/", context.AskView.as_view(), name="knowledge_ask"),
    path(
        _W + "ask/conversations/",
        context.AskConversationListView.as_view(),
        name="ask_conversation_list",
    ),
    path(
        _W + "ask/conversations/<uuid:conversation_id>/",
        context.AskConversationDetailView.as_view(),
        name="ask_conversation_detail",
    ),
    path(_W + "storage/", upload.StorageUsageView.as_view(), name="storage_usage"),
]
