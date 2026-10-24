import uuid

from django.conf import settings
from django.db import models

from common.models import TimeStampModel
from knowledge.constants.enums import ArticleStatus
from knowledge.constants.settings import ARTICLE_TITLE_MAX_LENGTH


class KnowledgeArticle(TimeStampModel):
    """The Markdown body lives in `content`. Its UTF-8 size (`size_bytes`) counts toward
    the workspace quota, which is enforced by `quota_service`."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="knowledge_articles",
    )
    title = models.CharField(max_length=ARTICLE_TITLE_MAX_LENGTH)
    status = models.CharField(
        max_length=10, choices=ArticleStatus.choices, default=ArticleStatus.DRAFT
    )
    content = models.TextField(blank=True, default="")
    size_bytes = models.PositiveIntegerField(default=0)
    categories = models.ManyToManyField(
        "knowledge.KnowledgeCategory",
        through="knowledge.KnowledgeArticleCategory",
        related_name="articles",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "knowledge_article"
        indexes = [models.Index(fields=["workspace", "status", "-updated_at"])]


class KnowledgeArticleCategory(models.Model):
    article = models.ForeignKey(
        "knowledge.KnowledgeArticle", on_delete=models.CASCADE, related_name="links"
    )
    category = models.ForeignKey(
        "knowledge.KnowledgeCategory", on_delete=models.CASCADE, related_name="links"
    )

    class Meta:
        db_table = "knowledge_article_category"
        constraints = [
            models.UniqueConstraint(
                fields=["article", "category"], name="unique_article_category"
            )
        ]
