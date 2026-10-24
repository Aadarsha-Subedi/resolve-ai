"""Encrypts a user's API key for storage. Encryption, not hashing: the key has to be sent to
the provider, so it must be recoverable. The workspace and user ids are sealed inside the
ciphertext, so a row copied to another user or workspace fails to open."""

from ai.constants.settings import KEY_LAST4_LENGTH, SEAL_SEPARATOR
from common import crypto
from common.llm import LLMInvalidKeyError


def seal(workspace_id, user_id, api_key: str) -> str:
    return crypto.encrypt(
        SEAL_SEPARATOR.join([str(workspace_id), str(user_id), api_key])
    )


def unseal(workspace_id, user_id, token: str) -> str:
    """The plain key, to be used for one call and not stored or logged."""
    try:
        plain = crypto.decrypt(token)
    except crypto.InvalidToken:
        raise LLMInvalidKeyError() from None
    owner_workspace, _, rest = plain.partition(SEAL_SEPARATOR)
    owner_user, _, api_key = rest.partition(SEAL_SEPARATOR)
    if (
        owner_workspace != str(workspace_id)
        or owner_user != str(user_id)
        or not api_key
    ):
        raise LLMInvalidKeyError()
    return api_key


def last4(api_key: str) -> str:
    return api_key[-KEY_LAST4_LENGTH:]
