from django.db import models


class ArticleStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class IndexStatus(models.TextChoices):
    """Whether an upload's text has been extracted and made searchable."""

    PENDING = "pending", "Pending"
    INDEXING = "indexing", "Indexing"
    INDEXED = "indexed", "Indexed"
    FAILED = "failed", "Failed"


class UploadStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    READY = "ready", "Ready"
