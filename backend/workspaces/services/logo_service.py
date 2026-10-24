import uuid

from accounts.models import User
from common.exception.domain import (
    BadRequestException,
    ServiceUnavailableException,
)
from common.storage import get_storage
from common.storage.base import DirectUploadUnsupported
from workspaces.constants import errors, messages, permissions
from workspaces.constants.settings import (
    LOGO_CONTENT_TYPES,
    LOGO_KEY_PREFIX,
    LOGO_MAX_BYTES,
    LOGO_UPLOAD_URL_EXPIRY_SECONDS,
)
from workspaces.models import Workspace
from workspaces.services import access, hooks


def create_upload_url(user: User, workspace_id, content_type: str, size: int) -> dict:
    """Signed PUT URL for the browser. The size and type are part of the signature."""
    access.require_permission(user, workspace_id, permissions.WORKSPACE_UPDATE)
    key = (
        LOGO_KEY_PREFIX.format(workspace_id=workspace_id)
        + f"{uuid.uuid7().hex}.{LOGO_CONTENT_TYPES[content_type]}"
    )
    try:
        upload_url = get_storage().presign_put(
            key, content_type, size, LOGO_UPLOAD_URL_EXPIRY_SECONDS
        )
    except DirectUploadUnsupported:
        raise ServiceUnavailableException(
            messages.MESSAGE_LOGO_UPLOAD_UNSUPPORTED,
            error_code=errors.ERROR_LOGO_UPLOAD_UNSUPPORTED,
        ) from None
    return {
        "key": key,
        "upload_url": upload_url,
        "expires_in": LOGO_UPLOAD_URL_EXPIRY_SECONDS,
        "headers": {"Content-Type": content_type},
    }


def confirm_logo(user: User, workspace_id, key: str) -> Workspace:
    """After the browser PUT: verify the object really exists and fits, then use it."""
    membership = access.require_permission(
        user, workspace_id, permissions.WORKSPACE_UPDATE
    )
    if not key.startswith(LOGO_KEY_PREFIX.format(workspace_id=workspace_id)):
        raise _invalid()
    storage = get_storage()
    info = storage.head(key)
    if (
        info is None
        or info.size > LOGO_MAX_BYTES
        or info.content_type not in LOGO_CONTENT_TYPES
    ):
        if info is not None:
            storage.delete(key)  # never keep an object we refuse to use
        raise _invalid()
    workspace = membership.workspace
    old_key = workspace.logo_key
    workspace.logo_key = key
    workspace.save(update_fields=["logo_key", "updated_at"])
    if old_key and old_key != key:
        storage.delete(old_key)
    hooks.emit(workspace, user, hooks.ACTION_LOGO_CHANGED)
    return workspace


def remove_logo(user: User, workspace_id) -> None:
    membership = access.require_permission(
        user, workspace_id, permissions.WORKSPACE_UPDATE
    )
    workspace = membership.workspace
    if workspace.logo_key:
        get_storage().delete(workspace.logo_key)
        workspace.logo_key = ""
        workspace.save(update_fields=["logo_key", "updated_at"])
        hooks.emit(workspace, user, hooks.ACTION_LOGO_CHANGED)


def logo_url(workspace: Workspace) -> str | None:
    return get_storage().url(workspace.logo_key) if workspace.logo_key else None


def _invalid() -> BadRequestException:
    return BadRequestException(
        messages.MESSAGE_LOGO_INVALID, error_code=errors.ERROR_LOGO_INVALID
    )
