"""Builds the reranker. This is the only place that knows the vendor."""

from django.conf import settings

from common.rerank.base import Reranker
from common.rerank.cohere_provider import CohereReranker


def get_reranker() -> Reranker | None:
    """The Cohere reranker, or None when no key is configured (reranking is then skipped)."""
    api_key = settings.COHERE_API_KEY
    if not api_key:
        return None
    return CohereReranker(api_key=api_key)
