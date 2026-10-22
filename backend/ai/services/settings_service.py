"""Per-user, per-workspace AI settings: the mode, the model and the user's own API key."""

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from ai.constants import errors, messages
from ai.constants.settings import MODE_OWN_KEY, MODE_RESOLVE_AI
from ai.models import UserWorkspaceLLMSettings
from ai.services import hooks, key_vault
from common.exception.domain import (
    BadRequestException,
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


def get_settings(user: User, workspace_id) -> UserWorkspaceLLMSettings:
    """The user's row, or an unsaved one holding the defaults."""
    _require(user, workspace_id)
    return _load(user, workspace_id)


def _load(user: User, workspace_id) -> UserWorkspaceLLMSettings:
    return UserWorkspaceLLMSettings.objects.filter(
        workspace_id=workspace_id, user=user
    ).first() or UserWorkspaceLLMSettings(workspace_id=workspace_id, user=user)


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


def update_settings(
    user: User,
    workspace_id,
    *,
    mode: str | None = None,
    resolve_ai_model: str | None = None,
    own_provider: str | None = None,
    own_model: str | None = None,
    api_key: str | None = None,
) -> UserWorkspaceLLMSettings:
    membership = _require(user, workspace_id)
    current = _load(user, workspace_id)

    if resolve_ai_model is not None and resolve_ai_model not in RESOLVE_AI_MODELS:
        raise _model_not_allowed()

    # The key and model to store, decided and checked with the provider before any write.
    new_key = None
    provider_name = own_provider or current.own_provider
    model = own_model
    changes_own = (
        api_key is not None or own_provider is not None or own_model is not None
    )
    if changes_own:
        if api_key is not None:
            if not own_provider:
                raise BadRequestException(
                    messages.MESSAGE_PROVIDER_REQUIRED,
                    error_code=errors.ERROR_PROVIDER_REQUIRED,
                )
            new_key = api_key
        elif not current.has_key or (
            own_provider is not None and own_provider != current.own_provider
        ):
            # A stored key belongs to one provider; switching needs a new key.
            raise _key_required()
        if provider_name not in PROVIDERS:
            raise _model_not_allowed()
        if not model:
            keep = current.own_model if new_key is None else ""
            model = keep or DEFAULT_MODELS[provider_name]
        if model not in ALLOWED_MODELS[provider_name]:
            raise _model_not_allowed()
        key = new_key or key_vault.unseal(
            workspace_id, user.id, current.own_key_encrypted
        )
        _check_key(create_provider(provider_name, key, model))
    if mode == MODE_OWN_KEY and not (current.has_key or new_key):
        raise _key_required()

    with transaction.atomic():
        row, _ = UserWorkspaceLLMSettings.objects.select_for_update().get_or_create(
            workspace_id=workspace_id, user=user
        )
        previous_mode = row.mode
        if resolve_ai_model is not None:
            row.resolve_ai_model = resolve_ai_model
        if changes_own:
            row.own_provider = provider_name
            row.own_model = model
            row.own_key_checked_at = timezone.now()
            if new_key:
                row.own_key_encrypted = key_vault.seal(workspace_id, user.id, new_key)
                row.own_key_last4 = key_vault.last4(new_key)
        if mode is not None:
            row.mode = mode
        row.save()

    workspace = membership.workspace
    if new_key:
        hooks.emit(
            workspace,
            user,
            hooks.ACTION_KEY_SAVED,
            provider=provider_name,
            model=model,
        )
    if row.mode != previous_mode:
        hooks.emit(
            workspace,
            user,
            hooks.ACTION_MODE_CHANGED,
            previous=previous_mode,
            mode=row.mode,
        )
    return row


def remove_key(user: User, workspace_id) -> UserWorkspaceLLMSettings:
    """Forget the user's key. If it was in use, fall back to Resolve AI mode."""
    membership = _require(user, workspace_id)
    with transaction.atomic():
        row = (
            UserWorkspaceLLMSettings.objects.select_for_update()
            .filter(workspace_id=workspace_id, user=user)
            .first()
        )
        if row is None or not row.has_key:
            return _load(user, workspace_id)
        provider_name = row.own_provider
        previous_mode = row.mode
        row.own_provider = row.own_model = ""
        row.own_key_encrypted = row.own_key_last4 = ""
        row.own_key_checked_at = None
        row.mode = MODE_RESOLVE_AI
        row.save()
    hooks.emit(
        membership.workspace, user, hooks.ACTION_KEY_REMOVED, provider=provider_name
    )
    if previous_mode != row.mode:
        hooks.emit(
            membership.workspace,
            user,
            hooks.ACTION_MODE_CHANGED,
            previous=previous_mode,
            mode=row.mode,
        )
    return row


def delete_for_member(workspace_id, user_id) -> None:
    """A member who leaves or is removed takes their key with them."""
    UserWorkspaceLLMSettings.objects.filter(
        workspace_id=workspace_id, user_id=user_id
    ).delete()


def provider_for(user: User, workspace_id) -> ResolvedProvider:
    """The provider this user's calls in this workspace go to. The caller has already
    checked membership. Raises an LLMError if the choice cannot be served (no server key,
    unreadable stored key); callers fall back to plain search."""
    row = _load(user, workspace_id)
    if row.uses_own_key and row.has_key:
        api_key = key_vault.unseal(workspace_id, user.id, row.own_key_encrypted)
        # A model dropped from the allowlist since it was saved falls back to the default.
        model = (
            row.own_model
            if row.own_model in ALLOWED_MODELS.get(row.own_provider, ())
            else None
        )
        return ResolvedProvider(
            create_provider(row.own_provider, api_key, model), uses_resolve_ai=False
        )
    model = row.resolve_ai_model if row.resolve_ai_model in RESOLVE_AI_MODELS else None
    return ResolvedProvider(resolve_ai_provider(model), uses_resolve_ai=True)
