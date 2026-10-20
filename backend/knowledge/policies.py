"""KnowledgePolicy: state-based (ABAC) rules that narrow the RBAC grants."""

from common.exception.domain import ConflictException
from knowledge.constants import errors, messages
from knowledge.constants.enums import ArticleStatus
from knowledge.models import KnowledgeArticle


class KnowledgePolicy:
    @staticmethod
    def can_edit_article(article: KnowledgeArticle) -> bool:
        """Archived articles are read-only until moved back to draft."""
        return article.status != ArticleStatus.ARCHIVED

    @staticmethod
    def ensure_can_edit(article: KnowledgeArticle) -> None:
        if not KnowledgePolicy.can_edit_article(article):
            raise ConflictException(
                messages.MESSAGE_ARTICLE_IS_ARCHIVED,
                error_code=errors.ERROR_ARTICLE_ARCHIVED,
            )
