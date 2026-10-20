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

## 5. Planned flows (not implemented yet; see the LLD, section 12)

Mark each as implemented, with real file references, when built: Google login, Connect Gmail, public ticket creation, agent reply, AI-assisted reply, inbound Gmail (Pub/Sub push and manual sync button).
