from django.db import models


class ArticleStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class UploadStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    READY = "ready", "Ready"
