from dataclasses import dataclass

from common.response.domain import BaseResponseData
from knowledge.models import (
    AskConversation,
    KnowledgeArticle,
    KnowledgeCategory,
    KnowledgeUpload,
)
from knowledge.services.answer_service import AnswerResult
from knowledge.services.context_service import ContextResult


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


@dataclass(frozen=True)
class ContextData(BaseResponseData):
    result: ContextResult

    def to_dict(self) -> dict:
        r = self.result
        return {
            "terms": r.terms,
            "queries": r.rewrites,
            "rewritten": r.rewritten,
            "results": [
                {
                    "citation": number,
                    "score": p.score,
                    "article": {"id": p.article_id, "title": p.article_title},
                    "section": p.section,
                    "chunk_id": p.chunk_id,
                    "snippet": p.snippet,
                }
                for number, p in enumerate(r.results, start=1)
            ],
        }


def answer_payload(result: AnswerResult) -> dict:
    """What one Ask turn shows: the context payload plus the answer. This is also what is stored."""
    return {
        **ContextData(result.context).to_dict(),
        "status": result.status,
        "reason": result.reason or None,
        "answer": result.answer or None,
        "cited": result.cited,
    }


@dataclass(frozen=True)
class AnswerData(BaseResponseData):
    """A new turn: the payload plus where it was stored. `status` says why `answer` is empty."""

    result: AnswerResult

    def to_dict(self) -> dict:
        turn = self.result.turn
        return {
            "conversation_id": str(turn.conversation_id),
            "turn_id": str(turn.id),
            "question": turn.question,
            "created_at": turn.created_at.isoformat(),
            **answer_payload(self.result),
        }


def _turn(turn) -> dict:
    return {
        "turn_id": str(turn.id),
        "question": turn.question,
        "created_at": turn.created_at.isoformat(),
        **turn.result,
    }


@dataclass(frozen=True)
class ConversationData(BaseResponseData):
    conversation: AskConversation
    with_turns: bool = False

    def to_dict(self) -> dict:
        c = self.conversation
        data = {
            "id": str(c.id),
            "title": c.title,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        if self.with_turns:
            data["turns"] = [_turn(t) for t in c.turns.all()]
        else:
            data["turn_count"] = getattr(c, "turn_count", None)
        return data
