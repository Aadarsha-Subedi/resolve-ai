"""Keeps `KnowledgeChunk` rows in step with their article.

Chunks exist for every article whatever its status (the search filters on the article's
status), and are rewritten only when the title or the content changes. Call
`rebuild_chunks` inside the transaction that saves the article, so a failure undoes both
and search never sees stale text.
"""

from django.db import connections, transaction
from django.db.models import F, QuerySet

from knowledge.models import KnowledgeArticle, KnowledgeChunk
from knowledge.services.chunker import chunk_markdown
from workspaces.models import Workspace


def fill_vectors(chunks: QuerySet[KnowledgeChunk]) -> None:
    """Compute `search_vector` from heading (weight A) and text (weight B) in each row's
    own language. Postgres only: on other databases the column stays NULL."""
    if connections[chunks.db].vendor != "postgresql":
        return
    from django.contrib.postgres.search import SearchVector

    chunks.update(
        search_vector=(
            SearchVector("heading_path", weight="A", config=F("search_language"))
            + SearchVector("text", weight="B", config=F("search_language"))
        )
    )


def _language(workspace_id) -> str:
    return Workspace.all_objects.values_list("search_language", flat=True).get(
        pk=workspace_id
    )


def rebuild_chunks(article: KnowledgeArticle, language: str | None = None) -> int:
    """Replace the article's chunks with ones made from its current title and content.
    Returns how many chunks were written."""
    language = language or _language(article.workspace_id)
    KnowledgeChunk.objects.filter(article=article).delete()
    drafts = chunk_markdown(article.title, article.content)
    KnowledgeChunk.objects.bulk_create(
        [
            KnowledgeChunk(
                workspace_id=article.workspace_id,
                article=article,
                position=position,
                heading_path=draft.heading_path,
                text=draft.text,
                search_language=language,
            )
            for position, draft in enumerate(drafts)
        ]
    )
    fill_vectors(KnowledgeChunk.objects.filter(article=article))
    return len(drafts)


def reindex_language(workspace_id) -> int:
    """The workspace language changed: stamp the new language on its chunks and recompute
    their vectors. The passages themselves do not change, so nothing is re-split."""
    language = _language(workspace_id)
    with transaction.atomic():
        chunks = KnowledgeChunk.objects.filter(workspace_id=workspace_id)
        count = chunks.update(search_language=language)
        fill_vectors(chunks)
    return count


def reindex_articles(workspace_id=None, dry_run: bool = False) -> tuple[int, int]:
    """Re-split and re-index every article (of one workspace, or of all). Returns
    (articles, chunks); with `dry_run` nothing is written and chunks is 0."""
    articles = KnowledgeArticle.objects.all().order_by("workspace_id", "id")
    if workspace_id is not None:
        articles = articles.filter(workspace_id=workspace_id)
    languages = dict(Workspace.all_objects.values_list("id", "search_language"))
    article_count = chunk_count = 0
    for article in articles.iterator(chunk_size=200):
        article_count += 1
        if dry_run:
            continue
        with transaction.atomic():
            chunk_count += rebuild_chunks(article, languages[article.workspace_id])
    return article_count, chunk_count
