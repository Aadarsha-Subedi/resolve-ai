import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.base import AuthError
from django.conf import settings

from accounts import redirects
from accounts.constants import errors
from accounts.constants.settings import (
    DISPLAY_NAME_MAX_LENGTH,
    SESSION_NEXT_KEY,
    SESSION_REMEMBER_KEY,
)
from accounts.models import User
from common.email.utils import normalize_email

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    def login(self, request, user) -> None:
        super().login(request, user)
        remember = bool(request.session.pop(SESSION_REMEMBER_KEY, False))
        request.session.set_expiry(
            settings.SESSION_REMEMBER_ME_AGE
            if remember
            else settings.SESSION_COOKIE_AGE
        )

    def get_login_redirect_url(self, request) -> str:
        return redirects.app_redirect_url(request.session.pop(SESSION_NEXT_KEY, None))

    def get_signup_redirect_url(self, request) -> str:
        # First sign-in goes through allauth's signup path.
        return self.get_login_redirect_url(request)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin) -> None:
        emails = sociallogin.email_addresses
        if not emails or not emails[0].verified:
            self._reject(errors.GOOGLE_ERROR_EMAIL_UNVERIFIED)
        if sociallogin.is_existing:
            user = sociallogin.user
            if not user.is_active:
                self._reject(errors.GOOGLE_ERROR_ACCOUNT_DISABLED)
            picture = sociallogin.account.extra_data.get("picture", "")
            if picture and picture != user.avatar_url:
                user.avatar_url = picture
                user.save(update_fields=["avatar_url", "updated_at"])
        elif User.objects.filter(email=normalize_email(emails[0].email)).exists():
            # Never link by email: that address belongs to an account with another Google `sub`.
            self._reject(errors.GOOGLE_ERROR_EMAIL_CONFLICT)

    def populate_user(self, request, sociallogin, data):
        user = sociallogin.user
        extra = sociallogin.account.extra_data
        email = normalize_email(data.get("email") or "")
        user.email = email
        user.display_name = (extra.get("name") or email.split("@")[0])[
            :DISPLAY_NAME_MAX_LENGTH
        ]
        user.avatar_url = extra.get("picture", "")
        return user

    def on_authentication_error(
        self, request, provider, error=None, exception=None, extra_context=None
    ) -> None:
        if exception is not None:
            logger.warning("Google sign-in failed: %s", type(exception).__name__)
        code = (
            errors.GOOGLE_ERROR_CANCELLED
            if error == AuthError.CANCELLED
            else errors.GOOGLE_ERROR_FAILED
        )
        self._reject(code)

    @staticmethod
    def _reject(code: str) -> None:
        raise ImmediateHttpResponse(redirects.login_error_redirect(code))
