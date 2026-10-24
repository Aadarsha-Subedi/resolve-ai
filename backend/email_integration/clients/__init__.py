from email_integration.clients.base import GmailClient
from email_integration.services import token_service


def get_gmail_client(connection) -> GmailClient:
    """Composition root: the real client for a connection's decrypted refresh token.
    Tests replace this function with one that returns a FakeGmailClient."""
    from email_integration.clients.rest import RestGmailClient

    return RestGmailClient(token_service.decrypt_refresh_token(connection))
