from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from accounts.models import User
from common.exception.domain import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    ValidationException,
)
from knowledge import policies
from knowledge.constants import errors, messages
from knowledge.constants.enums import ArticleStatus
from knowledge.constants.settings import ARTICLE_MAX_BYTES
from knowledge.models import (
    KnowledgeArticle,
    KnowledgeArticleCategory,
    KnowledgeCategory,
)
from knowledge.services import chunk_service, hooks, quota_service
from workspaces.constants import permissions
from workspaces.services import access

ORDERING_FIELDS = {"title", "created_at", "updated_at", "published_at"}
DEFAULT_ORDERING = "-updated_at"


def _size(content: str) -> int:
    size = len(content.encode("utf-8"))
    if size > ARTICLE_MAX_BYTES:
        raise ValidationException(
            messages.MESSAGE_ARTICLE_TOO_LARGE.format(
                limit_kb=ARTICLE_MAX_BYTES // 1024
            ),
            error_code=errors.ERROR_ARTICLE_TOO_LARGE,
        )
    return size


def _categories(workspace_id, category_ids) -> list[KnowledgeCategory]:
    ids = set(category_ids)
    found = list(
        KnowledgeCategory.objects.filter(workspace_id=workspace_id, pk__in=ids)
    )
    if len(found) != len(ids):
        raise ValidationException(messages.MESSAGE_CATEGORIES_INVALID)
    return found


def _set_categories(article: KnowledgeArticle, categories) -> None:
    KnowledgeArticleCategory.objects.filter(article=article).delete()
    KnowledgeArticleCategory.objects.bulk_create(
        [KnowledgeArticleCategory(article=article, category=c) for c in categories]
    )


def get_article(workspace_id, article_id) -> KnowledgeArticle:
    article = (
        KnowledgeArticle.objects.prefetch_related("categories")
        .filter(workspace_id=workspace_id, pk=article_id)
        .first()
    )
    if article is None:
        raise NotFoundException(messages.MESSAGE_ARTICLE_NOT_FOUND)
    return article


def create_article(
    user: User, workspace_id, title: str, content: str, category_ids
) -> KnowledgeArticle:
    membership = access.require_permission(
        user, workspace_id, permissions.KNOWLEDGE_MANAGE
    )
    size = _size(content)
    categories = _categories(workspace_id, category_ids)
    with transaction.atomic():
        quota_service.ensure_article_capacity(workspace_id)
        quota_service.reserve(workspace_id, size)
        article = KnowledgeArticle(
            workspace_id=workspace_id,
            title=title,
            content=content,
            size_bytes=size,
            created_by=user,
            updated_by=user,
        )
        article.save()
        _set_categories(article, categories)
        chunk_service.rebuild_chunks(article, membership.workspace.search_language)
    hooks.emit(
        membership.workspace,
        user,
        hooks.ACTION_ARTICLE_CREATED,
        target_id=str(article.id),
    )
    return get_article(workspace_id, article.id)


def update_article(
    user: User,
    workspace_id,
    article_id,
    title: str | None,
    content: str | None,
    category_ids,
) -> KnowledgeArticle:
    membership = access.require_permission(
        user, workspace_id, permissions.KNOWLEDGE_MANAGE
    )
    categories = (
        _categories(workspace_id, category_ids) if category_ids is not None else None
    )
    new_size = _size(content) if content is not None else None
    with transaction.atomic():
        article = (
            KnowledgeArticle.objects.select_for_update()
            .filter(workspace_id=workspace_id, pk=article_id)
            .first()
        )
        if article is None:
            raise NotFoundException(messages.MESSAGE_ARTICLE_NOT_FOUND)
        policies.KnowledgePolicy.ensure_can_edit(article)
        reindex = (title is not None and title != article.title) or (
            content is not None and content != article.content
        )
        if title is not None:
            article.title = title
        if categories is not None:
            _set_categories(article, categories)
        if new_size is not None:
            delta = new_size - article.size_bytes
            if delta > 0:
                quota_service.reserve(workspace_id, delta)
            else:
                quota_service.release(workspace_id, -delta)
            article.content = content
            article.size_bytes = new_size
        article.updated_by = user
        article.save()
        if reindex:
            chunk_service.rebuild_chunks(article, membership.workspace.search_language)
    hooks.emit(
        membership.workspace,
        user,
        hooks.ACTION_ARTICLE_UPDATED,
        target_id=str(article_id),
    )
    return get_article(workspace_id, article_id)


def delete_article(user: User, workspace_id, article_id) -> None:
    membership = access.require_permission(
        user, workspace_id, permissions.KNOWLEDGE_MANAGE
    )
    with transaction.atomic():
        article = (
            KnowledgeArticle.objects.select_for_update()
            .filter(workspace_id=workspace_id, pk=article_id)
            .first()
        )
        if article is None:
            raise NotFoundException(messages.MESSAGE_ARTICLE_NOT_FOUND)
        size = article.size_bytes
        article.delete()
        quota_service.release(workspace_id, size)
    hooks.emit(
        membership.workspace,
        user,
        hooks.ACTION_ARTICLE_DELETED,
        target_id=str(article_id),
    )


_TRANSITIONS = {
    ArticleStatus.PUBLISHED: {ArticleStatus.DRAFT, ArticleStatus.ARCHIVED},
    ArticleStatus.DRAFT: {ArticleStatus.PUBLISHED, ArticleStatus.ARCHIVED},
    ArticleStatus.ARCHIVED: {ArticleStatus.DRAFT, ArticleStatus.PUBLISHED},
}
_ACTIONS = {
    ArticleStatus.PUBLISHED: hooks.ACTION_ARTICLE_PUBLISHED,
    ArticleStatus.DRAFT: hooks.ACTION_ARTICLE_UNPUBLISHED,
    ArticleStatus.ARCHIVED: hooks.ACTION_ARTICLE_ARCHIVED,
}


def change_status(
    user: User, workspace_id, article_id, target: str
) -> KnowledgeArticle:
    membership = access.require_permission(
        user, workspace_id, permissions.KNOWLEDGE_MANAGE
    )
    with transaction.atomic():
        article = (
            KnowledgeArticle.objects.select_for_update()
            .filter(workspace_id=workspace_id, pk=article_id)
            .first()
        )
        if article is None:
            raise NotFoundException(messages.MESSAGE_ARTICLE_NOT_FOUND)
        if target not in _TRANSITIONS[article.status]:
            raise ConflictException(
                messages.MESSAGE_INVALID_TRANSITION.format(
                    current=article.status, target=target
                ),
                error_code=errors.ERROR_INVALID_TRANSITION,
            )
        article.status = target
        if target == ArticleStatus.PUBLISHED:
            article.published_at = timezone.now()
        article.updated_by = user
        article.save()
    hooks.emit(membership.workspace, user, _ACTIONS[target], target_id=str(article_id))
    return get_article(workspace_id, article_id)


def list_articles(
    user: User,
    workspace_id,
    title: str | None = None,
    status: str | None = None,
    category=None,
    ordering: str | None = None,
) -> QuerySet[KnowledgeArticle]:
    """Filter by title (contains), status and category (id). Plain queries, no full-text search."""
    access.require_permission(user, workspace_id, permissions.KNOWLEDGE_VIEW)
    queryset = KnowledgeArticle.objects.filter(workspace_id=workspace_id)
    if title:
        queryset = queryset.filter(title__icontains=title)
    if status:
        queryset = queryset.filter(status=status)
    if category:
        queryset = queryset.filter(Q(categories__pk=category))
    ordering = ordering or DEFAULT_ORDERING
    if ordering.lstrip("-") not in ORDERING_FIELDS:
        raise BadRequestException(
            f"Order by one of: {', '.join(sorted(ORDERING_FIELDS))}."
        )
    # Lists never show the body, so do not load up to 200 KB per row.
    return (
        queryset.defer("content")
        .prefetch_related("categories")
        .order_by(ordering, "id")
        .distinct()
    )
