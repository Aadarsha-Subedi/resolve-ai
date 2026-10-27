"""Reranking of the best fused passages with a cross-encoder (Cohere).

Reciprocal rank fusion only combines ranks; the reranker reads the question and each passage
together and judges relevance directly. It is an improvement, never a requirement: with no
key, over the workspace's daily limit, or on any provider error, `rerank` returns None and the
caller keeps the fused order. The question and the candidate passages' text are sent to the
provider, and the candidates always come from the workspace's own visible passages."""

import logging
from datetime import UTC, datetime

from django.conf import settings
from django.core.cache import cache

from common.rerank import RerankError, get_reranker
from knowledge.constants import settings as cfg

logger = logging.getLogger(__name__)


def _usage_key(workspace_id) -> str:
    return cfg.RERANK_USAGE_KEY.format(
        workspace_id=workspace_id, day=datetime.now(UTC).date().isoformat()
    )


def _reserve(workspace_id) -> bool:
    """Count one reranked search against the workspace's day; False (nothing counted) when
    the limit is reached."""
    key = _usage_key(workspace_id)
    cache.add(key, 0, cfg.EMBED_USAGE_TTL_SECONDS)
    if cache.incr(key) > settings.RERANK_DAILY_LIMIT:
        cache.decr(key)
        return False
    return True


def rerank(
    workspace_id, query: str, documents: list[str], top_n: int
) -> list[tuple[int, float]] | None:
    """(index into `documents`, relevance score) for the best `top_n`, best first; None when
    reranking did not happen."""
    if not documents or not query.strip():
        return None
    reranker = get_reranker()
    if reranker is None:
        return None
    if not _reserve(workspace_id):
        logger.info("Rerank skipped: daily limit reached")
        return None
    try:
        return reranker.rerank(query, documents, top_n)
    except RerankError as exc:
        cache.decr(_usage_key(workspace_id))  # a failed request is not counted
        logger.warning("Rerank skipped: %s", exc.code)
        return None
