from unittest import mock

import httpx
import openai
from django.test import SimpleTestCase, override_settings
from google.genai import errors as genai_errors

from common.llm import (
    LLMBadResponseError,
    LLMInvalidKeyError,
    LLMRateLimitedError,
    LLMRequest,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMUnsupportedError,
    create_provider,
    resolve_ai_provider,
)
from common.llm.constants import (
    ALLOWED_MODELS,
    DEFAULT_MODELS,
    EMBED_DOCUMENT,
    EMBED_QUERY,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    PROVIDERS,
    REQUEST_TIMEOUT_SECONDS,
    RESOLVE_AI_MODELS,
)
from common.llm.fake import FakeProvider, fake_embedding
from common.llm.gemini import GeminiProvider
from common.llm.openai_provider import OpenAIProvider

REQUEST = LLMRequest(prompt="hello", system="be brief", json_output=True)


class AllowlistTests(SimpleTestCase):
    def test_defaults_are_allowed(self):
        for provider in PROVIDERS:
            self.assertIn(DEFAULT_MODELS[provider], ALLOWED_MODELS[provider])

    def test_resolve_ai_models_are_a_subset_of_gemini(self):
        self.assertLessEqual(set(RESOLVE_AI_MODELS), set(ALLOWED_MODELS["gemini"]))
        self.assertIn(DEFAULT_MODELS["gemini"], RESOLVE_AI_MODELS)


class FactoryTests(SimpleTestCase):
    def test_creates_each_provider_with_its_default_model(self):
        gemini = create_provider("gemini", "key")
        openai_provider = create_provider("openai", "key")
        self.assertIsInstance(gemini, GeminiProvider)
        self.assertEqual(gemini.model, DEFAULT_MODELS["gemini"])
        self.assertIsInstance(openai_provider, OpenAIProvider)
        self.assertEqual(openai_provider.model, DEFAULT_MODELS["openai"])

    def test_unknown_provider_and_model_are_refused(self):
        with self.assertRaises(ValueError):
            create_provider("anthropic", "key")
        with self.assertRaises(ValueError):
            create_provider("gemini", "key", "gemini-unknown")
        with self.assertRaises(ValueError):
            create_provider("openai", "key", "gemini-3.1-flash-lite")

    @override_settings(GEMINI_API_KEY="server-key")
    def test_resolve_ai_provider_only_serves_cheap_models(self):
        self.assertEqual(resolve_ai_provider().model, DEFAULT_MODELS["gemini"])
        self.assertEqual(
            resolve_ai_provider("gemini-3.1-flash-lite").model, "gemini-3.1-flash-lite"
        )
        with self.assertRaises(ValueError):
            resolve_ai_provider("gemini-4-argon")

    @override_settings(GEMINI_API_KEY="")
    def test_resolve_ai_without_a_server_key_is_unavailable(self):
        with self.assertRaises(LLMUnavailableError):
            resolve_ai_provider()


class GeminiProviderTests(SimpleTestCase):
    def provider(self):
        with mock.patch("common.llm.gemini.genai.Client") as client_class:
            provider = GeminiProvider("secret-key", "gemini-3.5-flash-lite")
        self.client_class = client_class
        self.models = provider._client.models
        return provider

    def test_client_gets_a_timeout_in_milliseconds_and_no_retries(self):
        self.provider()
        options = self.client_class.call_args.kwargs["http_options"]
        self.assertEqual(options.timeout, REQUEST_TIMEOUT_SECONDS * 1000)
        self.assertEqual(options.retry_options.attempts, 1)

    def test_generate_returns_text_and_usage(self):
        provider = self.provider()
        self.models.generate_content.return_value = mock.Mock(
            text='{"a": 1}',
            usage_metadata=mock.Mock(prompt_token_count=5, candidates_token_count=3),
        )
        response = provider.generate(REQUEST)
        self.assertEqual(
            (response.text, response.input_tokens, response.output_tokens),
            ('{"a": 1}', 5, 3),
        )
        kwargs = self.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-3.5-flash-lite")
        self.assertEqual(kwargs["contents"], "hello")
        self.assertEqual(kwargs["config"].system_instruction, "be brief")
        self.assertEqual(kwargs["config"].response_mime_type, "application/json")

    def test_thinking_is_kept_to_a_minimum(self):
        from google.genai import types

        from common.llm.gemini import _thinking_config

        self.assertEqual(
            _thinking_config("gemini-3.5-flash-lite").thinking_level,
            types.ThinkingLevel.MINIMAL,
        )
        self.assertEqual(
            _thinking_config("gemini-3.1-pro-preview").thinking_level,
            types.ThinkingLevel.LOW,
        )
        self.assertEqual(_thinking_config("gemini-2.5-flash").thinking_budget, 0)
        self.assertEqual(_thinking_config("gemini-2.5-pro").thinking_budget, 128)
        provider = self.provider()
        self.models.generate_content.return_value = mock.Mock(
            text="x", usage_metadata=None
        )
        provider.generate(REQUEST)
        config = self.models.generate_content.call_args.kwargs["config"]
        self.assertEqual(
            config.thinking_config.thinking_level, types.ThinkingLevel.MINIMAL
        )

    def test_retries_without_thinking_when_the_model_rejects_it(self):
        from google.genai import errors

        provider = self.provider()
        self.models.generate_content.side_effect = [
            errors.ClientError(400, {"error": {"message": "bad thinking level"}}),
            mock.Mock(text="ok", usage_metadata=None),
        ]
        self.assertEqual(provider.generate(REQUEST).text, "ok")
        self.assertIsNone(
            self.models.generate_content.call_args.kwargs["config"].thinking_config
        )

    def test_empty_answer_is_a_bad_response(self):
        provider = self.provider()
        self.models.generate_content.return_value = mock.Mock(
            text="  ", usage_metadata=None
        )
        with self.assertRaises(LLMBadResponseError):
            provider.generate(REQUEST)

    def test_errors_are_mapped_and_hide_the_cause(self):
        provider = self.provider()
        cases = [
            (
                genai_errors.ClientError(429, {"error": {"message": "quota"}}),
                LLMRateLimitedError,
            ),
            (
                genai_errors.ClientError(403, {"error": {"message": "denied"}}),
                LLMInvalidKeyError,
            ),
            (
                genai_errors.ClientError(
                    400, {"error": {"message": "API key not valid. secret-key"}}
                ),
                LLMInvalidKeyError,
            ),
            (
                genai_errors.ServerError(503, {"error": {"message": "down"}}),
                LLMUnavailableError,
            ),
            (httpx.ReadTimeout("slow"), LLMTimeoutError),
            (RuntimeError("boom secret-key"), LLMUnavailableError),
        ]
        for error, expected in cases:
            self.models.generate_content.side_effect = error
            with self.assertRaises(expected) as raised:
                provider.generate(REQUEST)
            self.assertNotIn("secret-key", str(raised.exception))
            self.assertIsNone(raised.exception.__cause__)

    def test_validate_key_reads_the_model_and_maps_errors(self):
        provider = self.provider()
        provider.validate_key()
        self.models.get.assert_called_once_with(model="gemini-3.5-flash-lite")
        self.models.get.side_effect = genai_errors.ClientError(
            403, {"error": {"message": "denied"}}
        )
        with self.assertRaises(LLMInvalidKeyError):
            provider.validate_key()


class OpenAIProviderTests(SimpleTestCase):
    def provider(self):
        with mock.patch("common.llm.openai_provider.openai.OpenAI") as client_class:
            provider = OpenAIProvider("secret-key", "gpt-5-mini")
        self.client_class = client_class
        self.client = provider._client
        return provider

    def api_error(self, cls, status):
        response = httpx.Response(
            status, request=httpx.Request("POST", "https://api.openai.com/v1/x")
        )
        return cls("nope secret-key", response=response, body=None)

    def test_client_gets_a_timeout_and_no_retries(self):
        self.provider()
        kwargs = self.client_class.call_args.kwargs
        self.assertEqual(kwargs["timeout"], REQUEST_TIMEOUT_SECONDS)
        self.assertEqual(kwargs["max_retries"], 0)

    def test_generate_returns_text_and_usage(self):
        provider = self.provider()
        self.client.chat.completions.create.return_value = mock.Mock(
            choices=[mock.Mock(message=mock.Mock(content="answer"))],
            usage=mock.Mock(prompt_tokens=7, completion_tokens=2),
        )
        response = provider.generate(REQUEST)
        self.assertEqual(
            (response.text, response.input_tokens, response.output_tokens),
            ("answer", 7, 2),
        )
        kwargs = self.client.chat.completions.create.call_args.kwargs
        self.assertEqual(
            kwargs["messages"],
            [
                {"role": "system", "content": "be brief"},
                {"role": "user", "content": "hello"},
            ],
        )
        self.assertEqual(kwargs["response_format"], {"type": "json_object"})
        self.assertNotIn("temperature", kwargs)

    def test_empty_answer_is_a_bad_response(self):
        provider = self.provider()
        self.client.chat.completions.create.return_value = mock.Mock(
            choices=[mock.Mock(message=mock.Mock(content=None))], usage=None
        )
        with self.assertRaises(LLMBadResponseError):
            provider.generate(REQUEST)

    def test_errors_are_mapped_and_hide_the_cause(self):
        provider = self.provider()
        cases = [
            (self.api_error(openai.AuthenticationError, 401), LLMInvalidKeyError),
            (self.api_error(openai.PermissionDeniedError, 403), LLMInvalidKeyError),
            (self.api_error(openai.RateLimitError, 429), LLMRateLimitedError),
            (self.api_error(openai.InternalServerError, 500), LLMUnavailableError),
            (
                openai.APITimeoutError(request=httpx.Request("POST", "https://x")),
                LLMTimeoutError,
            ),
        ]
        for error, expected in cases:
            self.client.chat.completions.create.side_effect = error
            with self.assertRaises(expected) as raised:
                provider.generate(REQUEST)
            self.assertNotIn("secret-key", str(raised.exception))
            self.assertIsNone(raised.exception.__cause__)

    def test_validate_key_retrieves_the_model(self):
        provider = self.provider()
        provider.validate_key()
        self.client.models.retrieve.assert_called_once_with("gpt-5-mini")
        self.client.models.retrieve.side_effect = self.api_error(
            openai.AuthenticationError, 401
        )
        with self.assertRaises(LLMInvalidKeyError):
            provider.validate_key()


class FakeProviderTests(SimpleTestCase):
    def test_queued_answers_errors_and_recorded_requests(self):
        fake = FakeProvider(answers=["one"])
        self.assertEqual(fake.generate(REQUEST).text, "one")
        self.assertEqual(fake.generate(REQUEST).text, "ok")
        fake.fail_with = LLMTimeoutError()
        with self.assertRaises(LLMTimeoutError):
            fake.generate(REQUEST)
        self.assertEqual(len(fake.requests), 3)
        fake.key_valid = False
        with self.assertRaises(LLMInvalidKeyError):
            fake.validate_key()


class OpenAIReasoningTests(SimpleTestCase):
    def call(self, model):
        with mock.patch("common.llm.openai_provider.openai.OpenAI"):
            provider = OpenAIProvider("secret-key", model)
        provider._client.chat.completions.create.return_value = mock.Mock(
            choices=[mock.Mock(message=mock.Mock(content="ok"))], usage=None
        )
        provider.generate(REQUEST)
        return provider._client.chat.completions.create.call_args.kwargs

    def test_gpt5_thinks_minimally_and_gets_more_room(self):
        kwargs = self.call("gpt-5-mini")
        self.assertEqual(kwargs["reasoning_effort"], "minimal")
        self.assertEqual(kwargs["max_completion_tokens"], REQUEST.max_output_tokens * 4)

    def test_other_models_are_left_alone(self):
        kwargs = self.call("gpt-4.1-mini")
        self.assertNotIn("reasoning_effort", kwargs)
        self.assertEqual(kwargs["max_completion_tokens"], REQUEST.max_output_tokens)


class OpenAIQuotaTests(SimpleTestCase):
    def test_a_429_for_no_credit_is_told_apart_from_a_rate_limit(self):
        from common.llm import LLMInsufficientQuotaError

        with mock.patch("common.llm.openai_provider.openai.OpenAI"):
            provider = OpenAIProvider("secret-key", "gpt-5-mini")
        response = httpx.Response(
            429, request=httpx.Request("POST", "https://api.openai.com/v1/x")
        )
        out_of_credit = openai.RateLimitError(
            "no", response=response, body={"code": "insufficient_quota"}
        )
        provider._client.chat.completions.create.side_effect = out_of_credit
        with self.assertRaises(LLMInsufficientQuotaError):
            provider.generate(REQUEST)
        busy = openai.RateLimitError(
            "slow down", response=response, body={"code": "rate_limit_exceeded"}
        )
        provider._client.chat.completions.create.side_effect = busy
        with self.assertRaises(LLMRateLimitedError) as caught:
            provider.generate(REQUEST)
        self.assertNotIsInstance(caught.exception, LLMInsufficientQuotaError)


class EmbeddingTests(SimpleTestCase):
    def gemini(self):
        with mock.patch("common.llm.gemini.genai.Client"):
            provider = GeminiProvider("secret-key", "gemini-3.5-flash-lite")
        return provider, provider._client.models

    @staticmethod
    def reply(count, size=EMBEDDING_DIMENSIONS):
        return mock.Mock(
            embeddings=[mock.Mock(values=[0.5] * size) for _ in range(count)]
        )

    def test_gemini_uses_the_fixed_model_and_size(self):
        provider, models = self.gemini()
        models.embed_content.return_value = self.reply(2)
        vectors = provider.embed(["a", "b"], EMBED_QUERY)
        self.assertEqual(len(vectors), 2)
        kwargs = models.embed_content.call_args.kwargs
        self.assertEqual(kwargs["model"], EMBEDDING_MODEL)
        self.assertEqual(kwargs["contents"], ["a", "b"])
        self.assertEqual(kwargs["config"].task_type, "RETRIEVAL_QUERY")
        self.assertEqual(kwargs["config"].output_dimensionality, EMBEDDING_DIMENSIONS)

    def test_documents_use_the_document_task(self):
        provider, models = self.gemini()
        models.embed_content.return_value = self.reply(1)
        provider.embed(["a"], EMBED_DOCUMENT)
        self.assertEqual(
            models.embed_content.call_args.kwargs["config"].task_type,
            "RETRIEVAL_DOCUMENT",
        )

    def test_large_inputs_are_sent_in_batches(self):
        provider, models = self.gemini()
        models.embed_content.side_effect = lambda **kw: self.reply(len(kw["contents"]))
        vectors = provider.embed(["t"] * (EMBEDDING_BATCH_SIZE + 5))
        self.assertEqual(len(vectors), EMBEDDING_BATCH_SIZE + 5)
        sizes = [c.kwargs["contents"] for c in models.embed_content.call_args_list]
        self.assertEqual([len(s) for s in sizes], [EMBEDDING_BATCH_SIZE, 5])

    def test_wrong_count_or_size_is_a_bad_response(self):
        provider, models = self.gemini()
        models.embed_content.return_value = self.reply(1)
        with self.assertRaises(LLMBadResponseError):
            provider.embed(["a", "b"])
        models.embed_content.return_value = self.reply(1, size=3)
        with self.assertRaises(LLMBadResponseError):
            provider.embed(["a"])

    def test_errors_are_mapped(self):
        provider, models = self.gemini()
        models.embed_content.side_effect = genai_errors.APIError(
            429, {"error": {"message": "quota for key secret-key"}}
        )
        with self.assertRaises(LLMRateLimitedError) as caught:
            provider.embed(["a"])
        self.assertNotIn("secret-key", str(caught.exception))

    def test_openai_does_not_embed(self):
        with mock.patch("common.llm.openai_provider.openai.OpenAI"):
            provider = OpenAIProvider("key", "gpt-5-mini")
        with self.assertRaises(LLMUnsupportedError):
            provider.embed(["a"])

    def test_fake_vectors_are_unit_length_and_reflect_shared_words(self):
        fake = FakeProvider()
        close, near, far = fake.embed(
            ["reset password", "password reset steps", "refund policy"]
        )
        self.assertEqual(len(close), EMBEDDING_DIMENSIONS)
        self.assertAlmostEqual(sum(v * v for v in close), 1.0)

        def dot(a, b):
            return sum(x * y for x, y in zip(a, b, strict=True))

        self.assertGreater(dot(close, near), dot(close, far))
        self.assertEqual(fake.embedded[0][1], EMBED_DOCUMENT)
        fake.fail_with = LLMTimeoutError()
        with self.assertRaises(LLMTimeoutError):
            fake.embed(["x"])
        self.assertEqual(fake_embedding("a b"), fake_embedding("b a"))
