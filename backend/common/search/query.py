"""Full-text search helpers shared by tickets, knowledge and the global search.

Postgres uses a stored `tsvector` column, `websearch_to_tsquery`, `ts_rank_cd` and
`ts_headline`. Any other database (the SQLite test escape hatch) falls back to a plain
case-insensitive "contains" on `fallback_fields`, with no ranking and no highlights, so
views and permissions still run in tests. Postgres-only behaviour is tested on Postgres.
"""

from django.db import connections
from django.db.models import F, Q, QuerySet, Value
from django.db.models.fields import FloatField

from common.exception.domain import ValidationException
from common.search import constants


def normalize_query(q: str | None) -> str | None:
    """Trim and collapse whitespace; None for empty input. Raises on bad length."""
    if q is None:
        return None
    q = " ".join(q.split())
    if not q:
        return None
    if len(q) < constants.QUERY_MIN_LENGTH:
        raise ValidationException(
            constants.MESSAGE_QUERY_TOO_SHORT.format(min=constants.QUERY_MIN_LENGTH),
            error_code=constants.ERROR_INVALID_SEARCH_QUERY,
        )
    if len(q) > constants.QUERY_MAX_LENGTH:
        raise ValidationException(
            constants.MESSAGE_QUERY_TOO_LONG.format(max=constants.QUERY_MAX_LENGTH),
            error_code=constants.ERROR_INVALID_SEARCH_QUERY,
        )
    return q


def _is_postgres(queryset: QuerySet) -> bool:
    return connections[queryset.db].vendor == "postgresql"


def _tsquery(q: str, config: str):
    from django.contrib.postgres.search import SearchQuery

    # "websearch" never raises on user input and supports quotes, "or" and -exclusion.
    return SearchQuery(q, config=config, search_type="websearch")


def search(
    queryset: QuerySet,
    q: str,
    *,
    config: str,
    vector_field: str,
    fallback_fields: tuple[str, ...] = (),
) -> QuerySet:
    """Keep rows matching `q` and annotate `rank` (0..1, higher is better).

    `vector_field` names a SearchVectorField (or an annotation producing one).
    `config` must come from the workspace whitelist, never from user input.
    Callers apply workspace and permission filters before calling this.
    """
    if _is_postgres(queryset):
        from django.contrib.postgres.search import SearchRank

        query = _tsquery(q, config)
        return queryset.filter(**{vector_field: query}).annotate(
            rank=SearchRank(
                F(vector_field),
                query,
                weights=constants.RANK_WEIGHTS,
                normalization=constants.RANK_NORMALIZATION,
                cover_density=True,
            )
        )
    condition = Q()
    for field in fallback_fields:
        condition |= Q(**{f"{field}__icontains": q})
    return queryset.filter(condition).annotate(
        rank=Value(0.0, output_field=FloatField())
    )


def order_by_relevance(
    queryset: QuerySet, tiebreak: tuple[str, ...] = ("-updated_at", "id")
) -> QuerySet:
    """Best match first; the tiebreak keeps pages stable."""
    return queryset.order_by("-rank", *tiebreak)


def search_with_query(queryset: QuerySet, query, *, vector_field: str) -> QuerySet:
    """Like `search`, for a prebuilt `SearchQuery` (for example the OR query from
    `common.search.context`). Postgres only: the caller handles other databases."""
    from django.contrib.postgres.search import SearchRank

    return queryset.filter(**{vector_field: query}).annotate(
        rank=SearchRank(
            F(vector_field),
            query,
            weights=constants.RANK_WEIGHTS,
            normalization=constants.RANK_NORMALIZATION,
            cover_density=True,
        )
    )


def with_headline(
    queryset: QuerySet,
    *,
    text_field: str,
    q: str | None = None,
    config: str,
    name: str = "headline",
    tsquery=None,
) -> QuerySet:
    """Annotate a snippet of `text_field` with matches wrapped in the highlight markers.

    `ts_headline` is expensive: call this only on the page of results being returned
    (for example on a queryset limited to the page's ids), never on all matches.
    Pass `tsquery` (a `SearchQuery`) instead of `q` to highlight a prebuilt query.
    """
    if not _is_postgres(queryset):
        return queryset.annotate(**{name: Value("")})
    from django.contrib.postgres.search import SearchHeadline

    return queryset.annotate(
        **{
            name: SearchHeadline(
                text_field,
                tsquery if tsquery is not None else _tsquery(q, config),
                config=config,
                start_sel=constants.HIGHLIGHT_START,
                stop_sel=constants.HIGHLIGHT_STOP,
                max_words=constants.HEADLINE_MAX_WORDS,
                min_words=constants.HEADLINE_MIN_WORDS,
            )
        }
    )
