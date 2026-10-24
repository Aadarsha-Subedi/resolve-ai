"""Turns a paragraph (a ticket, a customer message, a chat question) into a search query.

`websearch_to_tsquery` needs every word to match, which finds nothing for a paragraph. Here
the text is reduced to its most distinctive stemmed words (stop words dropped, at most
CONTEXT_MAX_TERMS) and joined with OR, so a passage matching a few of them still ranks.

Stemming and stop words come from the workspace's Postgres text search configuration, by
running `to_tsvector` in the database. Terms are cut down to letters and digits before they
are put into the query, so customer text can never inject tsquery syntax.
"""

import re
from dataclasses import dataclass

from django.contrib.postgres.search import SearchQuery
from django.db import connection

CONTEXT_MAX_TERMS = 12
CONTEXT_MAX_INPUT_CHARS = 5000
TERM_MIN_LENGTH = 2
TERM_MAX_LENGTH = 40

_WORD = re.compile(r"[^\W_]+", re.UNICODE)
# Only used when the database is not Postgres (tests); Postgres uses the language's own list.
_FALLBACK_STOP_WORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "has",
        "have",
        "i",
        "if",
        "in",
        "is",
        "it",
        "its",
        "me",
        "my",
        "of",
        "on",
        "or",
        "our",
        "so",
        "that",
        "the",
        "their",
        "them",
        "there",
        "they",
        "this",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "will",
        "with",
        "you",
        "your",
    ]
)


@dataclass(frozen=True)
class ContextQuery:
    terms: list[str]  # stemmed lexemes, most distinctive first
    query: (
        SearchQuery | None
    )  # None when the text holds no usable word (or not Postgres)
    raw: str = ""  # the tsquery text behind `query`, for tests and logs

    def __bool__(self) -> bool:
        return bool(self.terms)


def _clean(text: str) -> str:
    return " ".join(text.split())[:CONTEXT_MAX_INPUT_CHARS]


def _lexemes_postgres(text: str, config: str) -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT lexeme FROM unnest(to_tsvector(%s::regconfig, %s))", [config, text]
        )
        return [row[0] for row in cursor.fetchall()]


def _lexemes_fallback(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for word in _WORD.findall(text.lower()):
        if word not in _FALLBACK_STOP_WORDS:
            seen.setdefault(word)
    return list(seen)


def _safe(lexemes: list[str]) -> list[str]:
    """Keep plain alphanumeric terms only; a lexeme with anything else is dropped."""
    kept = []
    for lexeme in lexemes:
        if (
            TERM_MIN_LENGTH <= len(lexeme) <= TERM_MAX_LENGTH
            and _WORD.fullmatch(lexeme)
            and not lexeme.isdigit()
        ):
            kept.append(lexeme)
    return kept


def context_query(text: str | None, config: str) -> ContextQuery:
    """`config` must come from the workspace whitelist, never from user input."""
    text = _clean(text or "")
    if not text:
        return ContextQuery(terms=[], query=None)
    postgres = connection.vendor == "postgresql"
    lexemes = _lexemes_postgres(text, config) if postgres else _lexemes_fallback(text)
    # Longer words are rarer and more specific. `sorted` is stable, so ties keep the
    # alphabetical order Postgres returns, which makes the result deterministic.
    terms = sorted(_safe(lexemes), key=len, reverse=True)[:CONTEXT_MAX_TERMS]
    if not terms:
        return ContextQuery(terms=[], query=None)
    if not postgres:
        return ContextQuery(terms=terms, query=None)
    # 'simple': the terms are already stemmed, so they must not be stemmed again.
    raw = " | ".join(f"'{term}'" for term in terms)
    return ContextQuery(
        terms=terms,
        query=SearchQuery(raw, config="simple", search_type="raw"),
        raw=raw,
    )
