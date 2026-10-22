"""The one way application code makes an LLM call on behalf of a user in a workspace.

It picks the provider from the user's settings and enforces the daily allowance when the
call is paid for by the Resolve AI key. Callers catch `LLMError` and fall back."""

from accounts.models import User
from ai.services import allowance, settings_service
from common.llm import LLMRequest, LLMResponse


def generate(user: User, workspace_id, request: LLMRequest) -> LLMResponse:
    resolved = settings_service.provider_for(user, workspace_id)
    if resolved.uses_resolve_ai:
        allowance.consume(workspace_id, user.id)
    return resolved.provider.generate(request)
