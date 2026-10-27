"""Cohere Rerank v2 through the official SDK."""

import logging

import httpx
from cohere import ClientV2
from cohere.core.api_error import ApiError

from common.rerank.base import (
    RerankBadResponseError,
    Reranker,
    RerankError,
    RerankInvalidKeyError,
    RerankRateLimitedError,
    RerankTimeoutError,
    RerankUnavailableError,
)
from common.rerank.constants import (
    COHERE_RERANK_MODEL,
    PROVIDER_COHERE,
    REQUEST_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


def _map_error(exc: Exception) -> RerankError:
    # Class and status only: the provider's message can quote the key or the text.
    status = getattr(exc, "status_code", None)
    logger.warning("Cohere rerank failed: %s status=%s", type(exc).__name__, status)
    if isinstance(exc, httpx.TimeoutException):
        return RerankTimeoutError()
    if isinstance(exc, ApiError):
        if status in (401, 403):
            return RerankInvalidKeyError()
        if status == 429:
            return RerankRateLimitedError()
        if status in (408, 504):
            return RerankTimeoutError()
    return RerankUnavailableError()


class CohereReranker(Reranker):
    provider = PROVIDER_COHERE

    def __init__(self, api_key: str, model: str = COHERE_RERANK_MODEL):
        self.model = model
        self._client = ClientV2(
            api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=0
        )

    def rerank(
        self, query: str, documents: list[str], top_n: int
    ) -> list[tuple[int, float]]:
        if not documents:
            return []
        try:
            response = self._client.rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_n=min(top_n, len(documents)),
            )
        except Exception as exc:  # the SDK raises many types; callers get one family
            raise _map_error(exc) from exc
        try:
            ranked = [
                (int(item.index), float(item.relevance_score))
                for item in response.results
            ]
        except (AttributeError, TypeError, ValueError) as exc:
            raise RerankBadResponseError() from exc
        if any(not 0 <= index < len(documents) for index, _ in ranked):
            raise RerankBadResponseError()
        return ranked
