from common import crypto
from common.exception.domain import ServiceUnavailableException


def encrypt_refresh_token(token: str) -> str:
    return crypto.encrypt(token)


def decrypt_refresh_token(connection) -> str:
    try:
        return crypto.decrypt(connection.encrypted_refresh_token)
    except crypto.InvalidToken:
        # Wrong or rotated-away key: treat like a missing grant, never echo anything.
        raise ServiceUnavailableException(
            "Stored Gmail credentials cannot be read.",
            error_code="gmail_credentials_unreadable",
        ) from None
