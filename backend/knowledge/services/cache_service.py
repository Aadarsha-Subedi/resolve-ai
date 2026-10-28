"""Semantic cache of Ask answers (per workspace).

`lookup` embeds the question and finds the most similar cached question of the workspace that
the same provider and model answered; at or above CACHE_MIN_SIMILARITY the stored payload is
returned and no search or LLM call happens. On a miss the caller answers normally and `store`
keeps the new answer with the embedding `lookup` already made. Only answered questions are
stored. Every failure (no embedding key, daily limit, not Postgres) means "no cache": the
question is answered as before.

An entry is removed when the workspace's articles or uploads change (`clear`), and ignored
after CACHE_TTL_DAYS."""

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.db import connection
from django.utils import timezone
from pgvector.django import CosineDistance

from common.exception.domain import AppException
from common.llm import LLMError
from common.llm.constants import EMBEDDING_MODEL
from knowledge.constants import settings as cfg
from knowledge.models import AskCacheEntry
from knowledge.services import embedding_service

logger = logging.getLogger(__name__)


@dataclass
class Lookup:
    """What `lookup` learned: the question's vector (to store a new answer) and, on a hit, the
    cached payload with how close the cached question was."""

    vector: list[float]
    llm_model: str
    payload: dict | None = None
    similarity: float | None = None
    cached_question: str = ""


def lookup(user_id, workspace_id, text: str, llm_model: str) -> Lookup | None:
    """None when the cache cannot be used right now."""
    if connection.vendor != "postgresql" or not embedding_service.is_configured():
        return None
    try:
        vector = embedding_service.embed_queries(user_id, workspace_id, [text])[0]
    except (LLMError, AppException) as exc:
        logger.warning(
            "Answer cache skipped: %s",
            getattr(exc, "code", None) or getattr(exc, "error_code", ""),
        )
        return None
    oldest = timezone.now() - timedelta(days=cfg.CACHE_TTL_DAYS)
    nearest = (
        AskCacheEntry.objects.filter(
            workspace_id=workspace_id,
            embedding_model=EMBEDDING_MODEL,
            llm_model=llm_model,
            created_at__gte=oldest,
        )
        .annotate(distance=CosineDistance("embedding", vector))
        .order_by("distance")
        .first()
    )
    found = Lookup(vector, llm_model)
    if nearest is not None and 1 - nearest.distance >= cfg.CACHE_MIN_SIMILARITY:
        found.payload = nearest.payload
        found.similarity = round(1 - nearest.distance, 4)
        found.cached_question = nearest.question
    return found


def store(workspace_id, text: str, found: Lookup, payload: dict) -> None:
    try:
        AskCacheEntry.objects.create(
            workspace_id=workspace_id,
            question=text,
            embedding=found.vector,
            embedding_model=EMBEDDING_MODEL,
            llm_model=found.llm_model,
            payload=payload,
        )
    except Exception:
        logger.warning("Answer not cached", exc_info=True)


def clear(workspace_id) -> int:
    deleted, _ = AskCacheEntry.objects.filter(workspace_id=workspace_id).delete()
    return deleted
