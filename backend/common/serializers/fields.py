from rest_framework import serializers

from common.email.constants import EMAIL_MAX_LENGTH
from common.email.utils import normalize_email
from common.validators.email import EmailValidator


class NormalizedEmailField(serializers.CharField):
    """Email input: trimmed, lower-cased, then checked by the shared
    EmailValidator so every endpoint treats addresses the same way."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("max_length", EMAIL_MAX_LENGTH)
        super().__init__(**kwargs)
        self.validators.append(EmailValidator())

    def to_internal_value(self, data) -> str:
        return normalize_email(super().to_internal_value(data))
