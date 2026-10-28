"""The reranker interface and the errors every reranker maps its failures to."""

from abc import ABC, abstractmethod


class RerankError(Exception):
    """Base class. Messages are generic on purpose: they never contain keys or text."""

    code = "rerank_error"
    message = "The rerank request failed."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)


class RerankInvalidKeyError(RerankError):
    code = "rerank_invalid_key"
    message = "The API key was rejected."


class RerankRateLimitedError(RerankError):
    code = "rerank_rate_limited"
    message = "The provider rate limit was reached."


class RerankTimeoutError(RerankError):
    code = "rerank_timeout"
    message = "The provider did not answer in time."


class RerankUnavailableError(RerankError):
    code = "rerank_unavailable"
    message = "The provider is unavailable."


class RerankBadResponseError(RerankError):
    code = "rerank_bad_response"
    message = "The provider returned no usable answer."


class Reranker(ABC):
    provider: str
    model: str

    @abstractmethod
    def rerank(
        self, query: str, documents: list[str], top_n: int
    ) -> list[tuple[int, float]]:
        """The `top_n` most relevant documents as (index into `documents`, relevance score),
        best first. The score only orders documents (and may be compared with a threshold);
        it is not a probability and must not be mixed with other scores. Raises a
        RerankError subclass on any failure."""
