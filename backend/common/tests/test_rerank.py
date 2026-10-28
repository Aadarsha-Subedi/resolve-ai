from types import SimpleNamespace
from unittest import mock

import httpx
from cohere.core.api_error import ApiError
from django.test import SimpleTestCase, override_settings

from common.rerank import (
    RerankBadResponseError,
    RerankInvalidKeyError,
    RerankRateLimitedError,
    RerankTimeoutError,
    RerankUnavailableError,
    get_reranker,
)
from common.rerank.cohere_provider import CohereReranker


def _reranker(client) -> CohereReranker:
    reranker = CohereReranker(api_key="test-key")
    reranker._client = client
    return reranker


def _result(index, score):
    return SimpleNamespace(index=index, relevance_score=score)


class CohereRerankerTests(SimpleTestCase):
    def test_returns_index_and_score_best_first(self):
        client = mock.Mock()
        client.rerank.return_value = SimpleNamespace(
            results=[_result(2, 0.9), _result(0, 0.4)]
        )
        ranked = _reranker(client).rerank("q", ["a", "b", "c"], 2)
        self.assertEqual(ranked, [(2, 0.9), (0, 0.4)])
        self.assertEqual(client.rerank.call_args.kwargs["top_n"], 2)

    def test_top_n_is_capped_to_the_documents_sent(self):
        client = mock.Mock()
        client.rerank.return_value = SimpleNamespace(results=[_result(0, 0.5)])
        _reranker(client).rerank("q", ["a"], 5)
        self.assertEqual(client.rerank.call_args.kwargs["top_n"], 1)

    def test_out_of_range_index_is_a_bad_response(self):
        client = mock.Mock()
        client.rerank.return_value = SimpleNamespace(results=[_result(7, 0.5)])
        with self.assertRaises(RerankBadResponseError):
            _reranker(client).rerank("q", ["a"], 1)

    def test_errors_map_to_generic_codes_without_the_provider_message(self):
        cases = [
            (ApiError(status_code=401, body="key sk-secret"), RerankInvalidKeyError),
            (ApiError(status_code=429, body="slow"), RerankRateLimitedError),
            (ApiError(status_code=504, body="slow"), RerankTimeoutError),
            (httpx.ReadTimeout("slow"), RerankTimeoutError),
            (ApiError(status_code=500, body="boom"), RerankUnavailableError),
            (RuntimeError("boom"), RerankUnavailableError),
        ]
        for raised, expected in cases:
            client = mock.Mock()
            client.rerank.side_effect = raised
            with self.assertRaises(expected) as ctx:
                _reranker(client).rerank("q", ["a"], 1)
            self.assertNotIn("secret", str(ctx.exception))


class FactoryTests(SimpleTestCase):
    @override_settings(COHERE_API_KEY="")
    def test_no_key_means_no_reranker(self):
        self.assertIsNone(get_reranker())

    @override_settings(COHERE_API_KEY="test-key")
    def test_key_builds_the_cohere_reranker(self):
        self.assertIsInstance(get_reranker(), CohereReranker)
