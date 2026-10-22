from dataclasses import dataclass

from common.response.domain import BaseResponseData
from knowledge.models import KnowledgeArticle, KnowledgeCategory, KnowledgeUpload


def _category(category: KnowledgeCategory) -> dict:
    return {"id": str(category.id), "name": category.name, "slug": category.slug}


@dataclass(frozen=True)
class CategoryData(BaseResponseData):
    category: KnowledgeCategory

    def to_dict(self) -> dict:
        return {
            **_category(self.category),
            "created_at": self.category.created_at.isoformat(),
        }


@dataclass(frozen=True)
class ArticleData(BaseResponseData):
    article: KnowledgeArticle
    content: str | None = None  # only the detail view returns the body

    def to_dict(self) -> dict:
        a = self.article
        data = {
            "id": str(a.id),
            "title": a.title,
            "status": a.status,
            "categories": [_category(c) for c in a.categories.all()],
            "size_bytes": a.size_bytes,
            "created_by": str(a.created_by_id) if a.created_by_id else None,
            "updated_by": str(a.updated_by_id) if a.updated_by_id else None,
            "created_at": a.created_at.isoformat(),
            "updated_at": a.updated_at.isoformat(),
            "published_at": a.published_at.isoformat() if a.published_at else None,
        }
        if self.content is not None:
            data["content"] = self.content
        return data


@dataclass(frozen=True)
class UploadData(BaseResponseData):
    upload: KnowledgeUpload
    extra: dict | None = None

    def to_dict(self) -> dict:
        u = self.upload
        return {
            "id": str(u.id),
            "filename": u.filename,
            "content_type": u.content_type,
            "size_bytes": u.size_bytes,
            "status": u.status,
            "category": _category(u.category) if u.category_id else None,
            "uploaded_by": str(u.uploaded_by_id) if u.uploaded_by_id else None,
            "created_at": u.created_at.isoformat(),
            **(self.extra or {}),
        }


@dataclass(frozen=True)
class DictData(BaseResponseData):
    payload: dict

    def to_dict(self) -> dict:
        return self.payload
