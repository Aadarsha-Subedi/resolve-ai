from rest_framework import serializers

from common.serializers.base import StrictSerializer
from knowledge.constants import messages
from knowledge.constants.enums import ArticleStatus
from knowledge.constants.settings import (
    ARTICLE_TITLE_MAX_LENGTH,
    CATEGORY_NAME_MAX_LENGTH,
    MAX_CATEGORIES_PER_ARTICLE,
    UPLOAD_CONTENT_TYPES,
    UPLOAD_FILENAME_MAX_LENGTH,
    UPLOAD_MAX_BYTES,
)

_title = serializers.CharField(
    max_length=ARTICLE_TITLE_MAX_LENGTH, trim_whitespace=True
)


def _category_ids(**kwargs):
    return serializers.ListField(
        child=serializers.UUIDField(),
        max_length=MAX_CATEGORIES_PER_ARTICLE,
        allow_empty=True,
        **kwargs,
    )


class CreateArticleSerializer(StrictSerializer):
    title = serializers.CharField(
        max_length=ARTICLE_TITLE_MAX_LENGTH, trim_whitespace=True
    )
    content = serializers.CharField(allow_blank=True, trim_whitespace=False)
    category_ids = _category_ids(required=False, default=list)


class UpdateArticleSerializer(StrictSerializer):
    title = serializers.CharField(
        required=False, max_length=ARTICLE_TITLE_MAX_LENGTH, trim_whitespace=True
    )
    content = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=False
    )
    category_ids = _category_ids(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(messages.MESSAGE_NOTHING_TO_UPDATE)
        return attrs


class ArticleFilterSerializer(serializers.Serializer):
    """Query-string filters (unknown parameters such as limit/offset are ignored)."""

    title = serializers.CharField(required=False, max_length=ARTICLE_TITLE_MAX_LENGTH)
    status = serializers.ChoiceField(required=False, choices=ArticleStatus.choices)
    category = serializers.UUIDField(required=False)
    ordering = serializers.CharField(required=False, max_length=30)


class CategorySerializer(StrictSerializer):
    name = serializers.CharField(
        max_length=CATEGORY_NAME_MAX_LENGTH, trim_whitespace=True
    )


class UploadUrlSerializer(StrictSerializer):
    filename = serializers.CharField(max_length=UPLOAD_FILENAME_MAX_LENGTH)
    content_type = serializers.ChoiceField(choices=list(UPLOAD_CONTENT_TYPES))
    size = serializers.IntegerField(min_value=1, max_value=UPLOAD_MAX_BYTES)
