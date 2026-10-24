"""Daily allowance for calls on the Resolve AI key: LLM_CALL_LIMIT per user, per workspace,
per UTC day. Calls on a user's own key are not counted; their provider limits them.

The counter lives in the cache (Redis in production), so it is atomic across workers and
resets itself: yesterday's key is simply never read again."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.core.cache import cache

from common.llm import LLMError

KEY = "ai:allowance:{workspace_id}:{user_id}:{day}"
KEY_TTL_SECONDS = 2 * 24 * 60 * 60  # outlives the day it counts


class LLMAllowanceExhaustedError(LLMError):
    code = "llm_allowance_exhausted"
    message = "The daily Resolve AI allowance is used up."


@dataclass(frozen=True)
class Usage:
    used: int
    limit: int
    resets_at: datetime

    @property
    def remaining(self) -> int:
        return max(self.limit - self.used, 0)


def _today():
    return datetime.now(UTC).date()


def _key(workspace_id, user_id) -> str:
    return KEY.format(
        workspace_id=workspace_id, user_id=user_id, day=_today().isoformat()
    )


def _resets_at() -> datetime:
    tomorrow = _today() + timedelta(days=1)
    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=UTC)


def usage(workspace_id, user_id) -> Usage:
    used = int(cache.get(_key(workspace_id, user_id), 0))
    return Usage(used=used, limit=settings.LLM_CALL_LIMIT, resets_at=_resets_at())


def consume(workspace_id, user_id) -> None:
    """Count one call, or raise LLMAllowanceExhaustedError when the day's allowance is spent.
    The call is counted before it is made: a failed call still used the provider's quota."""
    key = _key(workspace_id, user_id)
    cache.add(key, 0, KEY_TTL_SECONDS)
    count = cache.incr(key)
    if count > settings.LLM_CALL_LIMIT:
        raise LLMAllowanceExhaustedError()
