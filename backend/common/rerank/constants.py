"""Reranker model and timeout. The model name lives here, not in logic."""

PROVIDER_COHERE = "cohere"
COHERE_RERANK_MODEL = "rerank-v5.0-pro"
REQUEST_TIMEOUT_SECONDS = 60  # a rerank that is slower is skipped, never waited for
