from unittest import mock
from urllib.parse import parse_qs, urlsplit

from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from django.conf import settings
from django.urls import resolve
from rest_framework.test import APIClient

from accounts.models import User
from accounts.services.identity import get_google_subject
from accounts.tests.base import (
    CALLBACK,
    START,
    AccountsTestCase,
    google_identity,
)
from common.throttling.scoped import AuthScopedThrottle

FRONT = settings.FRONTEND_URL.rstrip("/")


class GoogleStartTests(AccountsTestCase):
    def test_start_redirects_to_google_with_pkce_and_state(self):
        response = self.client.get(START)
        self.assertEqual(response.status_code, 302)
        parts = urlsplit(response["Location"])
        self.assertEqual(parts.netloc, "accounts.google.com")
        query = parse_qs(parts.query)
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertTrue(query["state"][0])
        self.assertIn("openid", query["scope"][0])
        self.assertEqual(query["prompt"], ["select_account"])
        self.assertTrue(query["redirect_uri"][0].endswith(CALLBACK))

    def test_start_accepts_only_get(self):
        self.assertEqual(self.client.post(START).status_code, 405)

    def test_allauth_account_and_token_urls_not_reachable(self):
        for path in (
            "/accounts/login/",
            "/accounts/signup/",
            "/accounts/password/reset/",
            "/api/auth/google/login/token/",
            "/api/auth/google/login/",
        ):
            self.assertEqual(self.client.get(path).status_code, 404, path)


class GoogleStartSignedInTests(AccountsTestCase):
    def test_signed_in_user_goes_straight_to_the_app(self):
        self.sign_in()
        response = self.client.get(START + "?next=/inbox")
        self.assertEqual(response["Location"], f"{FRONT}/inbox")


class GoogleCallbackTests(AccountsTestCase):
    def test_first_login_creates_user_without_password(self):
        response = self.sign_in()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{FRONT}/app")
        user = User.objects.get(email="jane@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.display_name, "Jane Doe")
        self.assertEqual(user.avatar_url, "https://lh3.example.com/a/jane")
        self.assertEqual(get_google_subject(user), "g-123")
        self.assertEqual(User.objects.count(), 1)

    def test_repeat_login_reuses_user_and_refreshes_avatar(self):
        self.sign_in()
        User.objects.filter(email="jane@example.com").update(display_name="Custom")
        self.sign_in(
            google_identity(picture="https://lh3.example.com/a/new"), client=APIClient()
        )
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get()
        self.assertEqual(user.avatar_url, "https://lh3.example.com/a/new")
        self.assertEqual(
            user.display_name, "Custom"
        )  # a chosen name is not overwritten
        self.assertEqual(SocialAccount.objects.count(), 1)

    def test_unverified_email_rejected(self):
        response = self.sign_in(google_identity(verified=False))
        self.assertEqual(
            response["Location"], f"{FRONT}/login?google_error=email_unverified"
        )
        self.assertEqual(User.objects.count(), 0)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_email_held_by_other_account_rejected(self):
        self.make_user(email="jane@example.com")
        response = self.sign_in(google_identity(sub="someone-else"))
        self.assertEqual(
            response["Location"], f"{FRONT}/login?google_error=email_conflict"
        )
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(SocialAccount.objects.count(), 0)

    def test_inactive_user_rejected(self):
        self.sign_in()
        User.objects.update(is_active=False)
        client = APIClient()
        response = self.sign_in(client=client)
        self.assertEqual(
            response["Location"], f"{FRONT}/login?google_error=account_disabled"
        )
        self.assertNotIn("_auth_user_id", client.session)

    def test_state_mismatch_redirects_with_error(self):
        self.client.get(START)
        response = self.client.get(f"{CALLBACK}?code=abc&state=wrong")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"], f"{FRONT}/login?google_error=google_failed"
        )

    def test_callback_without_start_redirects_with_error(self):
        response = self.client.get(f"{CALLBACK}?code=abc&state=nothing")
        self.assertEqual(
            response["Location"], f"{FRONT}/login?google_error=google_failed"
        )

    def test_user_cancelled_at_google(self):
        start = self.client.get(START)
        state = parse_qs(urlsplit(start["Location"]).query)["state"][0]
        response = self.client.get(f"{CALLBACK}?error=access_denied&state={state}")
        self.assertEqual(response["Location"], f"{FRONT}/login?google_error=cancelled")

    def test_failed_code_exchange_redirects(self):
        from allauth.socialaccount.providers.oauth2.client import OAuth2Error

        start = self.client.get(START)
        state = parse_qs(urlsplit(start["Location"]).query)["state"][0]
        with mock.patch.object(
            GoogleOAuth2Adapter, "get_access_token_data", side_effect=OAuth2Error("x")
        ):
            response = self.client.get(f"{CALLBACK}?code=bad&state={state}")
        self.assertEqual(
            response["Location"], f"{FRONT}/login?google_error=google_failed"
        )
        self.assertEqual(User.objects.count(), 0)

    def test_next_path_is_honoured(self):
        response = self.sign_in(query="?next=/inbox/1")
        self.assertEqual(response["Location"], f"{FRONT}/inbox/1")

    def test_open_redirect_blocked(self):
        for bad in ("//evil.com", "https://evil.com", "/\\evil.com", "evil"):
            self.client.cookies.clear()
            response = self.sign_in(query=f"?next={bad}", client=APIClient())
            self.assertEqual(response["Location"], f"{FRONT}/app", bad)

    def test_session_key_rotates_on_login(self):
        self.client.get(START)
        before = self.client.session.session_key
        self.sign_in()
        self.assertNotEqual(self.client.session.session_key, before)

    def test_no_google_tokens_stored_or_returned(self):
        self.sign_in()
        self.assertFalse(
            SocialAccount.objects.get().socialtoken_set.exists(),
        )
        response = self.client.get("/api/me/")
        body = response.content.decode()
        self.assertNotIn("fake", body)
        self.assertNotIn("access_token", body)

    def test_deletion_cancelled_by_signing_in_again(self):
        client = self.login_client()
        user = User.objects.get()
        csrf = client.get("/api/csrf/").cookies["csrftoken"].value
        self.assertEqual(
            client.delete("/api/me/", HTTP_X_CSRFTOKEN=csrf).status_code, 200
        )
        user.refresh_from_db()
        self.assertIsNotNone(user.deletion_requested_at)
        self.sign_in(client=APIClient())
        user.refresh_from_db()
        self.assertIsNone(user.deletion_requested_at)


class RememberMeTests(AccountsTestCase):
    def test_default_session_lasts_14_days(self):
        self.sign_in()
        self.assertEqual(
            self.client.session.get_expiry_age(), settings.SESSION_COOKIE_AGE
        )
        self.assertEqual(settings.SESSION_COOKIE_AGE, 14 * 24 * 3600)

    def test_remember_me_lasts_30_days(self):
        self.sign_in(query="?remember=1")
        self.assertEqual(
            self.client.session.get_expiry_age(), settings.SESSION_REMEMBER_ME_AGE
        )
        self.assertEqual(settings.SESSION_REMEMBER_ME_AGE, 30 * 24 * 3600)

    def test_remember_off_flag_is_14_days(self):
        self.sign_in(query="?remember=0")
        self.assertEqual(
            self.client.session.get_expiry_age(), settings.SESSION_COOKIE_AGE
        )


class GoogleThrottleTests(AccountsTestCase):
    def rates(self, value):
        patched = {**AuthScopedThrottle.THROTTLE_RATES, "google": value}
        return mock.patch.object(AuthScopedThrottle, "THROTTLE_RATES", patched)

    def test_start_over_limit_redirects_rate_limited(self):
        with self.rates("2/min"):
            self.assertEqual(self.client.get(START).status_code, 302)
            self.assertEqual(self.client.get(START).status_code, 302)
            response = self.client.get(START)
        self.assertEqual(
            response["Location"], f"{FRONT}/login?google_error=rate_limited"
        )

    def test_callback_over_limit_redirects_rate_limited(self):
        with self.rates("1/min"):
            self.client.get(f"{CALLBACK}?code=a&state=b")
            response = self.client.get(f"{CALLBACK}?code=a&state=b")
        self.assertEqual(
            response["Location"], f"{FRONT}/login?google_error=rate_limited"
        )

    def test_limit_is_per_ip(self):
        with self.rates("1/min"):
            self.client.get(START, REMOTE_ADDR="10.0.0.1")
            blocked = self.client.get(START, REMOTE_ADDR="10.0.0.1")
            other = self.client.get(START, REMOTE_ADDR="10.0.0.2")
        self.assertIn("rate_limited", blocked["Location"])
        self.assertIn("accounts.google.com", other["Location"])


class RoutingTests(AccountsTestCase):
    def test_callback_route_name_matches_redirect_uri(self):
        self.assertEqual(resolve(CALLBACK).url_name, "google_callback")
