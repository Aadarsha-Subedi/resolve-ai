"""Metadata that is safe to keep forever: scalars only, no secrets, no message text,
no email addresses, bounded size."""

import json

from audit.constants import settings as cfg
from common.email.utils import mask_email


def _clean_scalar(value):
    if isinstance(value, bool) or value is None or isinstance(value, int | float):
        return value
    text = str(value)
    if cfg.EMAIL_PATTERN.fullmatch(text.strip()):
        return mask_email(text.strip())
    return text[: cfg.METADATA_MAX_STRING_LENGTH]


def sanitize_metadata(metadata: dict | None) -> dict:
    clean: dict = {}
    for key, value in (metadata or {}).items():
        key = str(key)
        if cfg.SENSITIVE_KEY_PATTERN.search(key):
            continue
        if isinstance(value, list | tuple | set):
            clean[key] = [
                _clean_scalar(v)
                for v in list(value)[: cfg.METADATA_MAX_LIST_ITEMS]
                if not isinstance(v, dict | list | tuple | set)
            ]
        elif isinstance(value, dict):
            continue  # nothing nested: flat facts only
        else:
            clean[key] = _clean_scalar(value)
    if len(json.dumps(clean, default=str)) > cfg.METADATA_MAX_JSON_LENGTH:
        return dict(cfg.TRUNCATED_MARKER)
    return clean
