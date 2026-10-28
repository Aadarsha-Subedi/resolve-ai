"""Gives each chunk its embedding (a vector that stands for its meaning), after the chunk is
saved. Embedding calls the Resolve AI key, so it runs in a background task and never blocks
saving an article or indexing an upload; a chunk without a vector is still found by the
full-text search. Each workspace has a daily cap on embedded chunks."""

import logging
from datetime import UTC, datetime
from itertools import batched

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, QuerySet

from ai.constants import settings as ai_cfg
from ai.services import usage_service
from common.llm import (
    LLMError,
    LLMRateLimitedError,
    LLMUnavailableError,
    resolve_ai_provider,
)
from common.llm.constants import (
    EMBED_DOCUMENT,
    EMBED_QUERY,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
    PROVIDER_GEMINI,
)
from knowledge.constants.settings import (
    EMBED_DAILY_CHUNK_LIMIT,
    EMBED_QUERY_DAILY_LIMIT,
    EMBED_QUERY_USAGE_KEY,
    EMBED_SOURCE_ARTICLE,
    EMBED_SOURCE_UPLOAD,
    EMBED_SOURCES,
    EMBED_SWEEP_SOURCES,
    EMBED_USAGE_KEY,
    EMBED_USAGE_TTL_SECONDS,
)
from knowledge.models import KnowledgeChunk

logger = logging.getLogger(__name__)


def _pending(chunks: QuerySet[KnowledgeChunk]) -> QuerySet[KnowledgeChunk]:
    """Chunks with no vector, or a vector from a model that is no longer the current one."""
    return chunks.filter(
        Q(embedding__isnull=True) | ~Q(embedding_model=EMBEDDING_MODEL)
    )


def _source_chunks(kind: str, source_id) -> QuerySet[KnowledgeChunk]:
    if kind not in EMBED_SOURCES:
        raise ValueError(f"Unknown chunk source: {kind}")
    field = "article_id" if kind == EMBED_SOURCE_ARTICLE else "upload_id"
    return KnowledgeChunk.objects.filter(**{field: source_id})


def _usage_key(workspace_id) -> str:
    return EMBED_USAGE_KEY.format(
        workspace_id=workspace_id, day=datetime.now(UTC).date().isoformat()
    )


def _reserve(workspace_id, count: int) -> bool:
    """Count `count` chunks against the workspace's day; False (and nothing counted) when
    that would pass the cap. The counter is in the cache, so it is atomic across workers."""
    key = _usage_key(workspace_id)
    cache.add(key, 0, EMBED_USAGE_TTL_SECONDS)
    if cache.incr(key, count) > EMBED_DAILY_CHUNK_LIMIT:
        cache.decr(key, count)
        return False
    return True


def _release(workspace_id, count: int) -> None:
    cache.decr(_usage_key(workspace_id), count)


def is_configured() -> bool:
    return bool(settings.GEMINI_API_KEY)


def embed_source(kind: str, source_id) -> int:
    """Embed the chunks of one article or upload that have no current vector. Returns how
    many were embedded. A provider error (rate limit, timeout...) is raised after the
    batches that succeeded are saved, so a retry only does what is left. Nothing happens,
    quietly, when the server has no Gemini key."""
    chunks = list(_pending(_source_chunks(kind, source_id)).order_by("position"))
    if not chunks or not is_configured():
        return 0
    provider = resolve_ai_provider()
    done = 0
    for batch in batched(chunks, EMBEDDING_BATCH_SIZE):
        if not _reserve(batch[0].workspace_id, len(batch)):
            logger.info("Embedding cap reached for workspace %s", batch[0].workspace_id)
            break
        try:
            vectors = provider.embed([c.embedding_input for c in batch], EMBED_DOCUMENT)
        except LLMError:
            _release(batch[0].workspace_id, len(batch))
            raise
        for chunk, vector in zip(batch, vectors, strict=True):
            chunk.embedding = vector
            chunk.embedding_model = EMBEDDING_MODEL
        with transaction.atomic():
            # A chunk replaced while we were embedding is gone; the update skips it.
            KnowledgeChunk.objects.bulk_update(batch, ["embedding", "embedding_model"])
        done += len(batch)
    return done


def pending_sources(limit: int = EMBED_SWEEP_SOURCES) -> list[tuple[str, str]]:
    """(kind, id) of up to `limit` articles/uploads with chunks still waiting for a vector."""
    if not is_configured():
        return []
    pending = _pending(KnowledgeChunk.objects.all())
    articles = (
        pending.filter(article__isnull=False)
        .order_by("article_id")
        .values_list("article_id", flat=True)
        .distinct()[:limit]
    )
    sources = [(EMBED_SOURCE_ARTICLE, str(i)) for i in articles]
    room = limit - len(sources)
    if room > 0:
        uploads = (
            pending.filter(upload__isnull=False)
            .order_by("upload_id")
            .values_list("upload_id", flat=True)
            .distinct()[:room]
        )
        sources += [(EMBED_SOURCE_UPLOAD, str(i)) for i in uploads]
    return sources


def reset_embeddings(workspace_id=None) -> int:
    """Forget every stored vector (of one workspace, or of all) so the sweeper recomputes
    them. Used after the embedding model or its settings change."""
    chunks = KnowledgeChunk.objects.all()
    if workspace_id is not None:
        chunks = chunks.filter(workspace_id=workspace_id)
    return chunks.update(embedding=None, embedding_model="")


def embed_queries(user_id, workspace_id, texts: list[str]) -> list[list[float]]:
    """Vectors for search queries (all in one request), in order. Counts one search against
    the user's daily limit. Raises an LLMError when embedding is not possible: the caller
    then searches by words alone."""
    if not is_configured():
        raise LLMUnavailableError()
    try:
        vectors = _embed_queries(user_id, workspace_id, texts)
    except LLMError as exc:
        _log_query_embedding(user_id, workspace_id, texts, exc.code)
        raise
    _log_query_embedding(user_id, workspace_id, texts)
    return vectors


def _log_query_embedding(user_id, workspace_id, texts, error_code: str = "") -> None:
    usage_service.record(
        workspace_id,
        user_id,
        ai_cfg.USAGE_FEATURE_EMBEDDING,
        ai_cfg.USAGE_OUTCOME_ERROR if error_code else ai_cfg.USAGE_OUTCOME_LLM_CALL,
        question=texts[0] if texts else "",
        provider=PROVIDER_GEMINI,
        model=EMBEDDING_MODEL,
        error_code=error_code,
        details={"texts": len(texts)},
    )


def _embed_queries(user_id, workspace_id, texts: list[str]) -> list[list[float]]:
    key = EMBED_QUERY_USAGE_KEY.format(
        workspace_id=workspace_id,
        user_id=user_id,
        day=datetime.now(UTC).date().isoformat(),
    )
    cache.add(key, 0, EMBED_USAGE_TTL_SECONDS)
    if cache.incr(key) > EMBED_QUERY_DAILY_LIMIT:
        raise LLMRateLimitedError()
    return resolve_ai_provider().embed(texts, EMBED_QUERY)
