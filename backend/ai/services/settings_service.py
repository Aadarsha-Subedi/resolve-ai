"""Per-user, per-workspace AI settings: the mode, the Resolve AI model and the user's own API keys
(at most one per provider)."""

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from ai.constants import errors, messages
from ai.constants.settings import MODE_OWN_KEY, MODE_RESOLVE_AI
from ai.models import UserWorkspaceLLMKey, UserWorkspaceLLMSettings
from ai.services import hooks, key_vault
from common.exception.domain import (
    BadRequestException,
    NotFoundException,
    ServiceUnavailableException,
    ValidationException,
)
from common.llm import (
    LLMError,
    LLMInvalidKeyError,
    LLMProvider,
    create_provider,
    resolve_ai_provider,
)
from common.llm.constants import (
    ALLOWED_MODELS,
    DEFAULT_MODELS,
    PROVIDERS,
    RESOLVE_AI_MODELS,
)
from workspaces.constants import permissions
from workspaces.services import access


@dataclass(frozen=True)
class ResolvedProvider:
    provider: LLMProvider
    uses_resolve_ai: bool  # True when the call is paid for by the Resolve AI key


def _require(user: User, workspace_id):
    return access.require_permission(user, workspace_id, permissions.AI_USE)


@dataclass(frozen=True)
class SettingsView:
    """The user's settings row (or defaults) and their saved keys, oldest first."""

    row: UserWorkspaceLLMSettings
    keys: list[UserWorkspaceLLMKey]


def _load(user: User, workspace_id) -> UserWorkspaceLLMSettings:
    return UserWorkspaceLLMSettings.objects.filter(
        workspace_id=workspace_id, user=user
    ).first() or UserWorkspaceLLMSettings(workspace_id=workspace_id, user=user)


def _keys(user: User, workspace_id) -> list[UserWorkspaceLLMKey]:
    return list(
        UserWorkspaceLLMKey.objects.filter(workspace_id=workspace_id, user=user)
    )


def get_settings(user: User, workspace_id) -> SettingsView:
    _require(user, workspace_id)
    return SettingsView(_load(user, workspace_id), _keys(user, workspace_id))


def _model_not_allowed() -> ValidationException:
    return ValidationException(
        messages.MESSAGE_MODEL_NOT_ALLOWED, error_code=errors.ERROR_MODEL_NOT_ALLOWED
    )


def _key_required() -> BadRequestException:
    return BadRequestException(
        messages.MESSAGE_KEY_REQUIRED, error_code=errors.ERROR_KEY_REQUIRED
    )


def _check_key(provider: LLMProvider) -> None:
    """Ask the provider whether the key works. Nothing is saved before this passes."""
    try:
        provider.validate_key()
    except LLMInvalidKeyError:
        raise BadRequestException(
            messages.MESSAGE_INVALID_KEY, error_code=errors.ERROR_INVALID_KEY
        ) from None
    except LLMError as exc:
        raise ServiceUnavailableException(
            messages.MESSAGE_KEY_CHECK_FAILED, error_code=exc.code
        ) from None


def _emit_mode_change(workspace, user, previous: str, current: str) -> None:
    if current != previous:
        hooks.emit(
            workspace,
            user,
            hooks.ACTION_MODE_CHANGED,
            previous=previous,
            mode=current,
        )


def update_settings(
    user: User,
    workspace_id,
    *,
    mode: str | None = None,
    resolve_ai_model: str | None = None,
    active_provider: str | None = None,
) -> SettingsView:
    """Change the mode, the Resolve AI model, or which saved key answers."""
    membership = _require(user, workspace_id)
    keys = _keys(user, workspace_id)
    have = {k.provider for k in keys}

    if resolve_ai_model is not None and resolve_ai_model not in RESOLVE_AI_MODELS:
        raise _model_not_allowed()
    if active_provider is not None and active_provider not in have:
        raise _key_required()
    if mode == MODE_OWN_KEY and not have:
        raise _key_required()

    with transaction.atomic():
        row, _ = UserWorkspaceLLMSettings.objects.select_for_update().get_or_create(
            workspace_id=workspace_id, user=user
        )
        previous_mode = row.mode
        if resolve_ai_model is not None:
            row.resolve_ai_model = resolve_ai_model
        if active_provider is not None:
            row.active_provider = active_provider
        if mode is not None:
            row.mode = mode
        if row.mode == MODE_OWN_KEY and row.active_provider not in have:
            row.active_provider = keys[0].provider
        row.save()
    _emit_mode_change(membership.workspace, user, previous_mode, row.mode)
    return SettingsView(row, keys)


def _provider_or_404(provider: str) -> str:
    if provider not in PROVIDERS:
        raise NotFoundException(messages.MESSAGE_PROVIDER_NOT_FOUND)
    return provider


def save_key(
    user: User,
    workspace_id,
    provider: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> SettingsView:
    """Add the key for `provider`, or edit it (a new key, a new model, or both).

    The provider checks the key before anything is saved. The first key a user saves
    becomes the active one and switches them to own-key mode."""
    membership = _require(user, workspace_id)
    _provider_or_404(provider)
    existing = UserWorkspaceLLMKey.objects.filter(
        workspace_id=workspace_id, user=user, provider=provider
    ).first()
    if existing is None and not api_key:
        raise _key_required()
    model = model or (existing.model if existing else DEFAULT_MODELS[provider])
    if model not in ALLOWED_MODELS[provider]:
        raise _model_not_allowed()
    plain = api_key or key_vault.unseal(workspace_id, user.id, existing.key_encrypted)
    _check_key(create_provider(provider, plain, model))

    with transaction.atomic():
        values = {"model": model, "checked_at": timezone.now()}
        if api_key:
            values["key_encrypted"] = key_vault.seal(workspace_id, user.id, api_key)
            values["key_last4"] = key_vault.last4(api_key)
        UserWorkspaceLLMKey.objects.update_or_create(
            workspace_id=workspace_id, user=user, provider=provider, defaults=values
        )
        row, _ = UserWorkspaceLLMSettings.objects.select_for_update().get_or_create(
            workspace_id=workspace_id, user=user
        )
        previous_mode = row.mode
        if not row.active_provider:
            row.active_provider = provider
            row.mode = MODE_OWN_KEY
            row.save()
    if api_key:
        hooks.emit(
            membership.workspace,
            user,
            hooks.ACTION_KEY_SAVED,
            provider=provider,
            model=model,
        )
    _emit_mode_change(membership.workspace, user, previous_mode, row.mode)
    return SettingsView(row, _keys(user, workspace_id))


def remove_key(user: User, workspace_id, provider: str) -> SettingsView:
    """Forget the key for `provider`. If it was the active one, the next saved key takes over,
    or the user falls back to Resolve AI when there is none."""
    membership = _require(user, workspace_id)
    _provider_or_404(provider)
    with transaction.atomic():
        removed, _ = UserWorkspaceLLMKey.objects.filter(
            workspace_id=workspace_id, user=user, provider=provider
        ).delete()
        row, _ = UserWorkspaceLLMSettings.objects.select_for_update().get_or_create(
            workspace_id=workspace_id, user=user
        )
        previous_mode = row.mode
        left = _keys(user, workspace_id)
        if row.active_provider not in {k.provider for k in left}:
            row.active_provider = left[0].provider if left else ""
            if not left:
                row.mode = MODE_RESOLVE_AI
            row.save()
    if removed:
        hooks.emit(
            membership.workspace, user, hooks.ACTION_KEY_REMOVED, provider=provider
        )
    _emit_mode_change(membership.workspace, user, previous_mode, row.mode)
    return SettingsView(row, left)


def delete_for_member(workspace_id, user_id) -> None:
    """A member who leaves or is removed takes their keys with them."""
    UserWorkspaceLLMKey.objects.filter(
        workspace_id=workspace_id, user_id=user_id
    ).delete()
    UserWorkspaceLLMSettings.objects.filter(
        workspace_id=workspace_id, user_id=user_id
    ).delete()


def provider_for(user: User, workspace_id) -> ResolvedProvider:
    """The provider this user's calls in this workspace go to. The caller has already
    checked membership. Raises an LLMError if the choice cannot be served (no server key,
    unreadable stored key); callers fall back to plain search."""
    row = _load(user, workspace_id)
    if row.uses_own_key:
        key = UserWorkspaceLLMKey.objects.filter(
            workspace_id=workspace_id, user=user, provider=row.active_provider
        ).first()
        if key is not None:
            api_key = key_vault.unseal(workspace_id, user.id, key.key_encrypted)
            # A model dropped from the allowlist since it was saved falls back to the default.
            model = (
                key.model if key.model in ALLOWED_MODELS.get(key.provider, ()) else None
            )
            return ResolvedProvider(
                create_provider(key.provider, api_key, model), uses_resolve_ai=False
            )
    model = row.resolve_ai_model if row.resolve_ai_model in RESOLVE_AI_MODELS else None
    return ResolvedProvider(resolve_ai_provider(model), uses_resolve_ai=True)
