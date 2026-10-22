"""Context search: the best passages of PUBLISHED articles for a piece of text.

The text can be a ticket, a customer's message or a question typed into the chat box. The
original text and up to three LLM rewrites of it are each searched (OR of the most
distinctive stemmed words, ranked with `ts_rank_cd`), and the ranked lists are merged with
reciprocal rank fusion. A passage that ranks well for several wordings rises to the top.
If rewriting fails for any reason, only the original text is searched."""

import hashlib
from dataclasses import dataclass, field

from django.contrib.postgres.search import SearchQuery
from django.core.cache import cache
from django.db import connection
from django.db.models import Q

from accounts.models import User
from ai.services.rewrite_service import rewrite_query
from common.search.context import ContextQuery, context_query
from common.search.query import search_with_query, with_headline
from knowledge.constants import settings as cfg
from knowledge.constants.enums import ArticleStatus
from knowledge.models import KnowledgeChunk
from workspaces.constants import permissions
from workspaces.services import access


@dataclass
class Passage:
    chunk_id: str
    article_id: str
    article_title: str
    section: str
    snippet: str
    score: float
    text: str = ""


@dataclass
class ContextResult:
    results: list[Passage] = field(default_factory=list)
    terms: list[str] = field(default_factory=list)
    rewrites: list[str] = field(default_factory=list)

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


def _published_chunks(workspace_id):
    return KnowledgeChunk.objects.filter(
        workspace_id=workspace_id, article__status=ArticleStatus.PUBLISHED
    )


def _ranked(workspace_id, query: ContextQuery) -> list[tuple[str, float]]:
    """(chunk id, score) for one query, best first."""
    base = _published_chunks(workspace_id)
    many = len(query.terms) >= cfg.CONTEXT_MANY_TERMS
    minimum = cfg.CONTEXT_MIN_SCORE_MANY_TERMS if many else cfg.CONTEXT_MIN_SCORE
    if connection.vendor == "postgresql":
        rows = (
            search_with_query(base, query.query, vector_field="search_vector")
            .filter(rank__gte=minimum)
            .order_by("-rank", "-article__updated_at", "id")
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


def _select(
    merged: list[tuple[str, float]], article_of: dict[str, str]
) -> list[tuple[str, float]]:
    """At most CONTEXT_MAX_PER_ARTICLE passages per article, CONTEXT_MAX_RESULTS in all."""
    per_article: dict[str, int] = {}
    picked = []
    for chunk_id, score in merged:
        article_id = article_of[chunk_id]
        if per_article.get(article_id, 0) >= cfg.CONTEXT_MAX_PER_ARTICLE:
            continue
        per_article[article_id] = per_article.get(article_id, 0) + 1
        picked.append((chunk_id, score))
        if len(picked) == cfg.CONTEXT_MAX_RESULTS:
            break
    return picked


def _combined_query(queries: list[ContextQuery]) -> ContextQuery:
    terms = list(dict.fromkeys(t for q in queries for t in q.terms))
    if connection.vendor != "postgresql" or not terms:
        return ContextQuery(terms=terms, query=None)
    raw = " | ".join(f"'{term}'" for term in terms)
    return ContextQuery(
        terms=terms, query=SearchQuery(raw, config="simple", search_type="raw"), raw=raw
    )


def retrieve_context(user: User, workspace, text: str) -> ContextResult:
    """Passages for `text`. The caller has checked the user's permission."""
    text = " ".join((text or "").split())
    original = context_query(text, workspace.search_language)
    if not original:
        return ContextResult()
    rewrites = _rewrites(user, workspace.id, text)
    queries = [original] + [
        q for q in (context_query(r, workspace.search_language) for r in rewrites) if q
    ]
    rankings = [_ranked(workspace.id, q) for q in queries]
    merged = _merge(rankings)
    if not merged:
        return ContextResult(terms=original.terms, rewrites=rewrites)

    article_of = {
        str(chunk_id): str(article_id)
        for chunk_id, article_id in _published_chunks(workspace.id)
        .filter(id__in=[c for c, _ in merged])
        .values_list("id", "article_id")
    }
    picked = _select([m for m in merged if m[0] in article_of], article_of)

    combined = _combined_query(queries)
    rows = _published_chunks(workspace.id).filter(id__in=[c for c, _ in picked])
    if combined.query is not None:
        rows = with_headline(
            rows,
            text_field="text",
            config=workspace.search_language,
            tsquery=combined.query,
        )
    by_id = {str(row.id): row for row in rows.select_related("article")}
    passages = []
    for chunk_id, score in picked:
        row = by_id[chunk_id]
        snippet = getattr(row, "headline", "") or row.text[:300]
        passages.append(
            Passage(
                chunk_id=chunk_id,
                article_id=str(row.article_id),
                article_title=row.article.title,
                section=row.heading_path,
                snippet=snippet,
                score=round(score, 4),
                text=row.text,
            )
        )
    return ContextResult(results=passages, terms=combined.terms, rewrites=rewrites)


def retrieve_for_question(user: User, workspace_id, text: str) -> ContextResult:
    """Chat box entry point: any member with `knowledge.view`."""
    membership = access.require_permission(
        user, workspace_id, permissions.KNOWLEDGE_VIEW
    )
    return retrieve_context(user, membership.workspace, text)
