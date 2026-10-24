"""Keeps `KnowledgeChunk` rows in step with their article or uploaded document.

Chunks exist for every article whatever its status (the search filters on the article's
status), and are rewritten only when the title or the content changes. Call
`rebuild_chunks` inside the transaction that saves the article, so a failure undoes both
and search never sees stale text. An uploaded document's chunks are written by
`rebuild_upload_chunks` in the transaction that marks the upload INDEXED.

A rewrite is incremental: a passage whose heading path, text and page are unchanged keeps
its row (same id, same search vector, and later the same embedding) even if its position
moves. Only passages that really changed are deleted and inserted.
"""

import os
from collections import defaultdict, deque

from django.db import connections, transaction
from django.db.models import F, QuerySet

from common.documents import ParsedDocument
from knowledge.constants.settings import EMBED_SOURCE_ARTICLE, EMBED_SOURCE_UPLOAD
from knowledge.models import KnowledgeArticle, KnowledgeChunk, KnowledgeUpload
from knowledge.services.chunker import ChunkDraft, chunk_document, chunk_markdown
from workspaces.models import Workspace

# Rows that change position are first parked above any real position, then placed, so the
# unique (source, position) constraint is never violated midway.
_PARK_OFFSET = 10_000_000


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


def _queue_embedding(kind: str, source_id) -> None:
    """Once the surrounding transaction commits, embed the source's new chunks."""
    from knowledge.tasks import embed_source  # tasks import this module

    transaction.on_commit(lambda: embed_source.delay(kind, str(source_id)))


def _sync(
    existing: QuerySet[KnowledgeChunk],
    drafts: list[ChunkDraft],
    language: str,
    make_row,
    embed_as: tuple[str, object],
    full: bool = False,
) -> int:
    """Make the rows of one source match `drafts`. Returns how many chunks the source has.
    `make_row(position, draft)` builds an unsaved row. With `full` every row is replaced.
    Rows that are new get their embedding afterwards (`embed_as` is the (kind, id) of the
    source); rows that were kept keep theirs."""
    rows = list(existing.order_by("position"))
    pool: dict[tuple, deque[KnowledgeChunk]] = defaultdict(deque)
    if not full:
        for row in rows:
            if row.search_language == language:
                pool[(row.heading_path, row.text, row.page)].append(row)
    kept: list[tuple[KnowledgeChunk, int]] = []
    new_rows: list[KnowledgeChunk] = []
    for position, draft in enumerate(drafts):
        candidates = pool.get((draft.heading_path, draft.text, draft.page))
        if candidates:
            kept.append((candidates.popleft(), position))
        else:
            new_rows.append(make_row(position, draft))
    kept_ids = {row.id for row, _ in kept}
    stale = [row.id for row in rows if row.id not in kept_ids]
    if stale:
        KnowledgeChunk.objects.filter(pk__in=stale).delete()
    moved = [(row, position) for row, position in kept if row.position != position]
    if moved:
        KnowledgeChunk.objects.filter(pk__in=[row.id for row, _ in moved]).update(
            position=F("position") + _PARK_OFFSET
        )
        for row, position in moved:
            row.position = position
        KnowledgeChunk.objects.bulk_update([row for row, _ in moved], ["position"])
    if new_rows:
        KnowledgeChunk.objects.bulk_create(new_rows)
        fill_vectors(KnowledgeChunk.objects.filter(pk__in=[r.id for r in new_rows]))
        _queue_embedding(*embed_as)
    return len(drafts)


def rebuild_chunks(
    article: KnowledgeArticle, language: str | None = None, full: bool = False
) -> int:
    """Make the article's chunks match its current title and content. Returns how many
    chunks the article has. With `full`, every row is replaced (vectors recomputed)."""
    language = language or _language(article.workspace_id)
    drafts = chunk_markdown(article.title, article.content)
    return _sync(
        KnowledgeChunk.objects.filter(article=article),
        drafts,
        language,
        lambda position, draft: KnowledgeChunk(
            workspace_id=article.workspace_id,
            article=article,
            position=position,
            heading_path=draft.heading_path,
            text=draft.text,
            search_language=language,
        ),
        (EMBED_SOURCE_ARTICLE, article.id),
        full=full,
    )


def upload_drafts(upload: KnowledgeUpload, parsed: ParsedDocument) -> list[ChunkDraft]:
    """The passages of a parsed document. The file name (without extension) is the title
    every heading path starts with."""
    title = os.path.splitext(upload.filename)[0]
    return chunk_document(title, [(p.number, p.markdown) for p in parsed.pages])


def rebuild_upload_chunks(
    upload: KnowledgeUpload,
    drafts: list[ChunkDraft],
    language: str | None = None,
    full: bool = False,
) -> int:
    """Make the upload's chunks match `drafts` (from `upload_drafts`)."""
    language = language or _language(upload.workspace_id)
    return _sync(
        KnowledgeChunk.objects.filter(upload=upload),
        drafts,
        language,
        lambda position, draft: KnowledgeChunk(
            workspace_id=upload.workspace_id,
            upload=upload,
            position=position,
            heading_path=draft.heading_path,
            text=draft.text,
            page=draft.page,
            search_language=language,
        ),
        (EMBED_SOURCE_UPLOAD, upload.id),
        full=full,
    )


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
            chunk_count += rebuild_chunks(
                article, languages[article.workspace_id], full=True
            )
    return article_count, chunk_count
