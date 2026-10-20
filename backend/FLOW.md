# FLOW.md

How code travels between files and functions. Update the relevant flow whenever a call path changes. References are `path::name`.

## 1. Any API request (implemented)

1. `common/logger/request_id.py::RequestIdMiddleware` assigns/accepts `X-Request-ID`, stores it in a context var, echoes it on the response.
2. Django session + auth middleware; `common/logger/request_id.py::UserContextMiddleware` records the user id for logs/Sentry.
3. `common/logger/middleware.py::RequestLoggingMiddleware` wraps the view; it logs method, route, redacted headers/body (`common/logger/redaction.py::redact_sensitive_data`), status and duration.
4. DRF throttles (`common/throttling/scoped.py::AnonThrottle`, `UserThrottle`, `WorkspaceThrottle`, plus per-view `AuthScopedThrottle` scopes from `config/settings.py::THROTTLE_RATES`).
5. View -> `Serializer.parse(request.data)` (`common/serializers/base.py::StrictSerializer.parse`) -> service function (business logic) -> `SuccessResponse` (`common/response/domain.py`).
6. Errors: services raise `common/exception/domain.py::AppException` subclasses; DRF validation/auth/throttle errors are mapped in `common/exception/handler.py::exception_handler` (strategy list of `BaseExceptionHandler`s) into `ErrorResponse`. Unknown exceptions fall through to a normal 500 (and Sentry via `common/observability/sentry.py::before_send`).

Health check: `config/urls.py` -> `common/urls.py` -> `common/views.py::HealthView.get` -> `SuccessResponse`.

## 2. File storage (implemented)

Caller -> `common/storage/__init__.py::get_storage()` (R2 if `R2_BUCKET_NAME`, else local disk) -> `FileStorage` methods in `common/storage/base.py`. Tests use `common/storage/memory.py::InMemoryStorage`.

## 3. Secrets at rest (implemented)

Service -> `common/crypto.py::encrypt/decrypt/rotate` using `settings.ENCRYPTION_KEYS`. Used later for `GmailConnection.encrypted_refresh_token`.

## 4. Caching (implemented)

`CacheModel.save/delete` and `SoftDeleteQuerySet.delete` -> `common/cache/manager.py::cache_manager` invalidate keys built by `keys_for`.

## 5. Google sign-in (implemented)

1. Browser -> `GET /api/auth/google/start/?remember=&next=` -> `accounts/views/google.py::GoogleStartView.get` (throttled `google` scope; throttled requests redirect with `google_error=rate_limited`). It stores the remember flag and a validated same-site `next` path in the session (`accounts/redirects.py::is_safe_next_path`), removes `next` from the request, and calls allauth's `oauth2_login`, which redirects to Google (PKCE, `state` in the session).
2. Google -> `GET /api/auth/google/login/callback/` -> `GoogleCallbackView.get` (same throttles) -> allauth `oauth2_callback`: checks `state`, exchanges the code, validates the ID token.
3. `accounts/adapters.py::SocialAccountAdapter.pre_social_login` rejects unverified email, inactive users and an email already held by another account (no linking by email); refreshes the avatar of a returning user. A new user is created by allauth auto-signup using `SocialAccountAdapter.populate_user`.
4. `AccountAdapter.login` logs in (session key rotates) and sets expiry: 30 days with remember me, else 14 days. The `user_logged_in` signal runs `accounts/signals.py::on_user_logged_in` -> `services/deletion_service.py::cancel_deletion` and emits the audit event.
5. `AccountAdapter.get_login_redirect_url` / `get_signup_redirect_url` redirect to `FRONTEND_URL` + `next` or `/app`. Any failure goes through `SocialAccountAdapter.on_authentication_error` to `FRONTEND_URL/login?google_error=<code>`.

## 6. Sessions and profile (implemented)

`/api/auth/sessions/` and `/api/auth/logout*` -> `accounts/views/session.py` -> `services/session_service.py` (allauth `UserSession` rows are created per authenticated request by `UserSessionsMiddleware`; `device.py::device_label` parses the user agent). `/api/me/` -> `views/profile.py::MeView` -> `profile_service.update_display_name` or `deletion_service.request_deletion` (runs `hooks.ownership_checks`, sets `deletion_requested_at`, ends all sessions). Daily beat tasks in `accounts/tasks.py` purge accounts past the 7-day grace and expired sessions.

## 7. Planned flows (not implemented yet; see the LLD, section 12)

Mark each as implemented, with real file references, when built: Connect Gmail, public ticket creation, agent reply, AI-assisted reply, inbound Gmail (Pub/Sub push and manual sync button).
