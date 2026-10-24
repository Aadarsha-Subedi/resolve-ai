"""In-memory provider for tests. Queue answers or an error, inspect `requests`."""

import hashlib
import math
import re

from common.llm.base import (
    LLMError,
    LLMProvider,
    LLMRequest,
    LLMResponse,
)
from common.llm.constants import EMBED_DOCUMENT, EMBEDDING_DIMENSIONS, PROVIDER_GEMINI


class FakeProvider(LLMProvider):
    provider = PROVIDER_GEMINI

    def __init__(self, model: str = "fake-model", answers: list[str] | None = None):
        self.model = model
        self.answers = list(answers or [])
        self.requests: list[LLMRequest] = []
        self.embedded: list[tuple[list[str], str]] = []  # (texts, task) per embed call
        self.fail_with: LLMError | None = None  # raised by the next call
        self.key_valid = True

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if self.fail_with is not None:
            error, self.fail_with = self.fail_with, None
            raise error
        text = self.answers.pop(0) if self.answers else "ok"
        return LLMResponse(text=text, model=self.model, input_tokens=1, output_tokens=1)

    def embed(self, texts: list[str], task: str = EMBED_DOCUMENT) -> list[list[float]]:
        """Bag-of-words vectors: texts that share words are close, so search tests behave."""
        self.embedded.append((list(texts), task))
        if self.fail_with is not None:
            error, self.fail_with = self.fail_with, None
            raise error
        return [fake_embedding(text) for text in texts]

    def validate_key(self) -> None:
        if not self.key_valid:
            from common.llm.base import LLMInvalidKeyError

            raise LLMInvalidKeyError()


def fake_embedding(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for word in re.findall(r"\w+", text.lower()):
        slot = int(hashlib.md5(word.encode()).hexdigest(), 16) % EMBEDDING_DIMENSIONS
        vector[slot] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]
