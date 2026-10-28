"""Context search: the best passages of PUBLISHED articles and READY uploaded documents for a
piece of text.

The text can be a ticket, a customer's message or a question typed into the chat box. The
original text and up to three LLM rewrites of it are each searched two ways: by words (OR of
the most distinctive stemmed words, ranked with BM25 from the ParadeDB index, or with
`ts_rank_cd` when the index is not available) and by meaning (the query's
embedding against the passages' embeddings, cosine similarity). All the ranked lists are
merged with reciprocal rank fusion, so a passage that ranks well for several wordings or in
both searches rises to the top. There is no limit per article or document: when one
document holds the answer, its passages fill the results.

Every step has a fallback: if rewriting fails only the original text is searched; if
embedding fails (no key, limit reached, provider down) or the database is not Postgres, only
the word search runs; if the word search finds nothing, the vector search alone decides."""

import hashlib
import logging
from dataclasses import dataclass, field

from django.contrib.postgres.search import SearchQuery
from django.core.cache import cache
from django.db import DatabaseError, connection, transaction
from django.db.models import Q

from accounts.models import User
from ai.services.rewrite_service import rewrite_query
from common.exception.domain import AppException
from common.llm import LLMError
from common.llm.constants import EMBEDDING_MODEL
from common.search.context import ContextQuery, context_query
from common.search.query import search_with_query, with_headline
from knowledge.constants import settings as cfg
from knowledge.constants.enums import ArticleStatus, UploadStatus
from knowledge.models import KnowledgeChunk
from knowledge.services import embedding_service, rerank_service
from workspaces.constants import permissions
from workspaces.services import access

logger = logging.getLogger(__name__)

SOURCE_ARTICLE = "article"
SOURCE_UPLOAD = "upload"


@dataclass
class Passage:
    chunk_id: str
    source_type: str  # SOURCE_ARTICLE or SOURCE_UPLOAD
    source_id: str
    source_title: str  # the article title, or the uploaded file's name
    section: str
    snippet: str
    score: float  # best raw score: BM25 (unbounded), ts_rank_cd (0 to 1) or vector similarity (0 to 1)
    text: str = ""
    page: int | None = None  # the PDF page, for passages of uploaded documents


@dataclass
class ContextResult:
    results: list[Passage] = field(default_factory=list)
    terms: list[str] = field(default_factory=list)
    rewrites: list[str] = field(default_factory=list)
    reranked: bool = False  # the order and scores come from the reranker (internal)

    @property
    def rewritten(self) -> bool:
        return bool(self.rewrites)


def _rewrites(user: User, workspace_id, text: str) -> list[str]:
    """Rewrites of `text`, remembered for an hour so repeated clicks cost no LLM call."""
    digest = hashlib.sha256(text.encode()).hexdigest()
    key = cfg.CONTEXT_REWRITE_CACHE_KEY.format(workspace_id=workspace_id, digest=digest)
    cached = cache.get(key)
    if cached is not None:
        return cached
    rewrites = rewrite_query(user, workspace_id, text)
    if rewrites:
        cache.set(key, rewrites, cfg.CONTEXT_REWRITE_CACHE_SECONDS)
    return rewrites


def _visible_chunks(workspace_id):
    """Passages of published articles and of uploads that are ready."""
    return KnowledgeChunk.objects.filter(workspace_id=workspace_id).filter(
        Q(article__status=ArticleStatus.PUBLISHED)
        | Q(upload__status=UploadStatus.READY)
    )


_BM25_SQL = """
SELECT id, pdb.score(id) AS score
FROM knowledge_chunk
WHERE bm25_terms ||| %s AND workspace_id = %s
ORDER BY score DESC
LIMIT %s
"""


def _bm25_ranked(workspace_id, query: ContextQuery) -> list[tuple[str, float]] | None:
    """(chunk id, BM25 score) for one query, best first, from the ParadeDB index; the query
    terms are the same stemmed lexemes `bm25_terms` holds. None when the index is not
    available, so the caller falls back to the tsvector search. The index covers all
    workspaces, so IDF is corpus-wide; the rows returned are this workspace's only, and
    only published articles and ready uploads."""
    many = len(query.terms) >= cfg.CONTEXT_MANY_TERMS
    min_hits = (
        cfg.CONTEXT_BM25_MIN_HITS_MANY_TERMS if many else cfg.CONTEXT_BM25_MIN_HITS
    )
    params = [" ".join(query.terms), str(workspace_id), cfg.CONTEXT_BM25_POOL]
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(_BM25_SQL, params)
            scored = [(str(row[0]), float(row[1])) for row in cursor.fetchall()]
    except DatabaseError as exc:
        logger.warning(
            "BM25 search is not available (%s): using the tsvector search",
            f"{type(exc).__name__}: {str(exc).splitlines()[0][:200] if str(exc) else ''}",
        )
        return None
    visible = dict(
        _visible_chunks(workspace_id)
        .filter(id__in=[chunk_id for chunk_id, _ in scored])
        .values_list("id", "bm25_terms")
    )
    visible = {str(chunk_id): terms or "" for chunk_id, terms in visible.items()}
    ranked = []
    for chunk_id, score in scored:
        if chunk_id not in visible:
            continue
        words = visible[chunk_id].split()
        if sum(words.count(term) for term in query.terms) >= min_hits:
            ranked.append((chunk_id, score))
    return ranked[: cfg.CONTEXT_CANDIDATES_PER_QUERY]


def _ranked(workspace_id, query: ContextQuery) -> list[tuple[str, float]]:
    """(chunk id, score) for one query by words, best first."""
    if connection.vendor == "postgresql":
        ranked = _bm25_ranked(workspace_id, query)
        if ranked is not None:
            return ranked
    base = _visible_chunks(workspace_id)
    many = len(query.terms) >= cfg.CONTEXT_MANY_TERMS
    minimum = cfg.CONTEXT_MIN_SCORE_MANY_TERMS if many else cfg.CONTEXT_MIN_SCORE
    if connection.vendor == "postgresql":
        rows = (
            search_with_query(base, query.query, vector_field="search_vector")
            .filter(rank__gte=minimum)
            .order_by("-rank", "-created_at", "id")
            .values_list("id", "rank")[: cfg.CONTEXT_CANDIDATES_PER_QUERY]
        )
        return [(str(chunk_id), float(rank)) for chunk_id, rank in rows]
    # Test fallback (no tsvector): any term contained in the passage, unranked.
    condition = Q()
    for term in query.terms:
        condition |= Q(text__icontains=term) | Q(heading_path__icontains=term)
    rows = (
        base.filter(condition)
        .order_by("id")
        .values_list("id", flat=True)[: cfg.CONTEXT_CANDIDATES_PER_QUERY]
    )
    return [(str(chunk_id), 0.0) for chunk_id in rows]


def _vector_rankings(
    workspace_id, vectors: list[list[float]]
) -> list[list[tuple[str, float]]]:
    """(chunk id, cosine similarity) per query vector, best first. Postgres only."""
    from pgvector.django import CosineDistance

    max_distance = 1 - cfg.CONTEXT_MIN_SIMILARITY
    rankings = []
    with transaction.atomic():
        try:
            # The index finds neighbours first and the workspace filter is applied after:
            # keep scanning until enough rows pass it (pgvector 0.8 and later).
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute("SET LOCAL hnsw.iterative_scan = strict_order")
        except DatabaseError:
            logger.info("pgvector iterative scan is not available")
        for vector in vectors:
            rows = (
                _visible_chunks(workspace_id)
                .filter(embedding__isnull=False, embedding_model=EMBEDDING_MODEL)
                .annotate(distance=CosineDistance("embedding", vector))
                .filter(distance__lte=max_distance)
                .order_by("distance", "id")
                .values_list("id", "distance")[: cfg.CONTEXT_CANDIDATES_PER_QUERY]
            )
            rankings.append(
                [(str(chunk_id), round(1 - float(d), 6)) for chunk_id, d in rows]
            )
    return rankings


def _query_vectors(user: User, workspace_id, texts: list[str]):
    """Embeddings of the query texts (one request), or None when searching by meaning is
    not possible right now."""
    if connection.vendor != "postgresql" or not embedding_service.is_configured():
        return None
    try:
        return embedding_service.embed_queries(user.id, workspace_id, texts)
    except (LLMError, AppException) as exc:
        logger.warning(
            "Search by meaning skipped: %s",
            getattr(exc, "code", None) or getattr(exc, "error_code", ""),
        )
        return None


def _merge(rankings: list[list[tuple[str, float]]]) -> list[tuple[str, float]]:
    """Reciprocal rank fusion. Returns (chunk id, best raw score), best fused first."""
    fused: dict[str, float] = {}
    best: dict[str, float] = {}
    for ranking in rankings:
        for position, (chunk_id, score) in enumerate(ranking, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (
                cfg.CONTEXT_RRF_K + position
            )
            best[chunk_id] = max(best.get(chunk_id, 0.0), score)
    ordered = sorted(fused, key=lambda c: (-fused[c], -best[c], c))
    return [(chunk_id, best[chunk_id]) for chunk_id in ordered]


def _combined_query(queries: list[ContextQuery]) -> ContextQuery:
    terms = list(dict.fromkeys(t for q in queries for t in q.terms))
    if connection.vendor != "postgresql" or not terms:
        return ContextQuery(terms=terms, query=None)
    raw = " | ".join(f"'{term}'" for term in terms)
    return ContextQuery(
        terms=terms, query=SearchQuery(raw, config="simple", search_type="raw"), raw=raw
    )


def _passage(row: KnowledgeChunk, score: float) -> Passage:
    snippet = getattr(row, "headline", "") or row.text[:300]
    if row.article_id:
        kind, source_id, title = SOURCE_ARTICLE, row.article_id, row.article.title
    else:
        kind, source_id, title = SOURCE_UPLOAD, row.upload_id, row.upload.filename
    return Passage(
        chunk_id=str(row.id),
        source_type=kind,
        source_id=str(source_id),
        source_title=title,
        section=row.heading_path,
        snippet=snippet,
        score=round(score, 4),
        text=row.text,
        page=row.page,
    )


def _rerank(
    user: User, workspace_id, text: str, candidates: list[tuple[str, float]], rows: dict
) -> tuple[list[tuple[str, float]], bool]:
    """The passages to keep as (chunk id, score), and whether the reranker ordered them. Falls
    back to the fused order (raw scores) when reranking did not happen."""
    limit = cfg.CONTEXT_MAX_RESULTS
    documents = [
        f"{rows[c].heading_path}\n{rows[c].text}"
        if rows[c].heading_path
        else rows[c].text
        for c, _ in candidates
    ]
    ranked = rerank_service.rerank(
        workspace_id, text, documents, limit, user_id=user.id
    )
    if ranked is None:
        return candidates[:limit], False
    picked = [
        (candidates[i][0], score)
        for i, score in ranked
        if score >= cfg.CONTEXT_RERANK_MIN_SCORE
    ]
    return picked[:limit], True


def retrieve_context(user: User, workspace, text: str) -> ContextResult:
    """Passages for `text`. The caller has checked the user's permission."""
    text = " ".join((text or "").split())
    original = context_query(text, workspace.search_language)
    if not original and not text:
        return ContextResult()
    rewrites = _rewrites(user, workspace.id, text)
    texts = [text, *rewrites]
    queries = [
        q for q in (context_query(t, workspace.search_language) for t in texts) if q
    ]
    rankings = [_ranked(workspace.id, q) for q in queries]
    vectors = _query_vectors(user, workspace.id, texts)
    if vectors:
        rankings += _vector_rankings(workspace.id, vectors)
    terms = original.terms if original else []
    merged = _merge(rankings)
    if not merged:
        return ContextResult(terms=terms, rewrites=rewrites)

    rows = {
        str(row.id): row
        for row in _visible_chunks(workspace.id)
        .filter(id__in=[c for c, _ in merged])
        .select_related("article", "upload")
    }
    candidates = [m for m in merged if m[0] in rows]
    candidates = candidates[
        : max(cfg.CONTEXT_RERANK_CANDIDATES, cfg.CONTEXT_MAX_RESULTS)
    ]
    picked, reranked = _rerank(user, workspace.id, text, candidates, rows)

    combined = _combined_query(queries)
    chosen = _visible_chunks(workspace.id).filter(id__in=[c for c, _ in picked])
    if combined.query is not None:
        headlines = {
            str(r.id): r.headline
            for r in with_headline(
                chosen,
                text_field="text",
                config=workspace.search_language,
                tsquery=combined.query,
            )
        }
        for chunk_id, headline in headlines.items():
            rows[chunk_id].headline = headline
    passages = [_passage(rows[chunk_id], score) for chunk_id, score in picked]
    return ContextResult(
        results=passages,
        terms=combined.terms or terms,
        rewrites=rewrites,
        reranked=reranked,
    )


def retrieve_for_question(user: User, workspace_id, text: str) -> ContextResult:
    """Chat box entry point: any member with `knowledge.view`."""
    membership = access.require_permission(
        user, workspace_id, permissions.KNOWLEDGE_VIEW
    )
    return retrieve_context(user, membership.workspace, text)
