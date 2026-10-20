from unittest import mock
from urllib.parse import parse_qs, urlsplit

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User

CALLBACK = "/api/auth/google/login/callback/"
START = "/api/auth/google/start/"
OAUTH_CODE = "authcode-9f8e7d"


def google_identity(sub="g-123", email="jane@example.com", verified=True, **extra):
    return {
        "sub": sub,
        "email": email,
        "email_verified": verified,
        "name": "Jane Doe",
        "picture": "https://lh3.example.com/a/jane",
        **extra,
    }


class AccountsTestCase(TestCase):
    """Drives the real allauth flow; only the network calls to Google are mocked."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def sign_in(self, identity=None, client=None, query="", ua="", ip=None):
        """start -> (Google, mocked) -> callback. Returns the callback response."""
        client = client or self.client
        extra = {"HTTP_USER_AGENT": ua} if ua else {}
        if ip:
            extra["REMOTE_ADDR"] = ip
        start = client.get(START + query, **extra)
        assert start.status_code == 302, start.status_code
        state = parse_qs(urlsplit(start["Location"]).query)["state"][0]
        identity = identity or google_identity()

        def complete_login(adapter, request, app, token, **kwargs):
            provider = adapter.get_provider()
            return provider.sociallogin_from_response(request, identity)

        with (
            mock.patch.object(
                GoogleOAuth2Adapter,
                "get_access_token_data",
                return_value={"access_token": "fake"},
            ),
            mock.patch.object(GoogleOAuth2Adapter, "complete_login", complete_login),
        ):
            return client.get(f"{CALLBACK}?code={OAUTH_CODE}&state={state}", **extra)

    def make_user(self, **kwargs) -> User:
        kwargs.setdefault("email", "other@example.com")
        return User.objects.create_user(**kwargs)

    def login_client(self, **kwargs) -> APIClient:
        client = APIClient(enforce_csrf_checks=False)
        self.assertEqual(self.sign_in(client=client, **kwargs).status_code, 302)
        return client


__all__ = ["AccountsTestCase", "google_identity", "mock", "override_settings"]
