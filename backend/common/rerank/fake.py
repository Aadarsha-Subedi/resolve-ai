"""A deterministic reranker for tests: the share of the query's words found in a document."""

import re

from common.rerank.base import Reranker, RerankError

_WORD = re.compile(r"[^\W_]+", re.UNICODE)


class FakeReranker(Reranker):
    provider = "fake"
    model = "fake-rerank"

    def __init__(self, error: RerankError | None = None):
        self.error = error
        self.calls: list[dict] = []

    def rerank(
        self, query: str, documents: list[str], top_n: int
    ) -> list[tuple[int, float]]:
        self.calls.append(
            {"query": query, "documents": list(documents), "top_n": top_n}
        )
        if self.error:
            raise self.error
        words = set(_WORD.findall(query.lower()))
        scored = []
        for index, document in enumerate(documents):
            found = words & set(_WORD.findall(document.lower()))
            scored.append((index, len(found) / len(words) if words else 0.0))
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:top_n]
