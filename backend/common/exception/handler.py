import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import set_rollback

from common.exception.domain import (
    AppException,
    AppExceptionHandler,
    BaseExceptionHandler,
)
from common.response.domain import ErrorResponse

logger = logging.getLogger(__name__)


def _flatten_errors(detail: object, prefix: str = "") -> list[dict]:
    """Turn DRF's nested error detail into [{"field": ..., "message": ...}]."""
    if isinstance(detail, dict):
        flat: list[dict] = []
        for key, value in detail.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            flat.extend(_flatten_errors(value, path))
        return flat
    if isinstance(detail, list):
        flat = []
        for item in detail:
            flat.extend(_flatten_errors(item, prefix))
        return flat
    return [{"field": prefix or None, "message": str(detail)}]


class DRFValidationErrorHandler(BaseExceptionHandler):
    """Maps serializer validation failures to a 400 with per-field errors."""

    def can_handle(self, exc: Exception) -> bool:
        return isinstance(exc, drf_exceptions.ValidationError)

    def handle(
        self, exc: drf_exceptions.ValidationError, context: dict
    ) -> ErrorResponse:
        return ErrorResponse(
            message="Validation failed.",
            errors=_flatten_errors(exc.detail),
            error_code="validation_error",
            status_code=400,
        )


class DRFAuthenticationErrorHandler(BaseExceptionHandler):
    """Maps missing or failed authentication to 401. SessionAuthentication
    gives no WWW-Authenticate header, so DRF would otherwise answer 403."""

    def can_handle(self, exc: Exception) -> bool:
        return isinstance(
            exc, (drf_exceptions.NotAuthenticated, drf_exceptions.AuthenticationFailed)
        )

    def handle(self, exc: drf_exceptions.APIException, context: dict) -> ErrorResponse:
        return ErrorResponse(
            message="You are not authenticated to perform this action.",
            error_code="authentication_denied",
            status_code=401,
        )


class DRFThrottledHandler(BaseExceptionHandler):
    """Maps throttling to 429 with a Retry-After header."""

    def can_handle(self, exc: Exception) -> bool:
        return isinstance(exc, drf_exceptions.Throttled)

    def handle(self, exc: drf_exceptions.Throttled, context: dict) -> ErrorResponse:
        response = ErrorResponse(
            message="Too many requests. Please try again later.",
            error_code="throttled",
            status_code=429,
        )
        if exc.wait is not None:
            response["Retry-After"] = str(int(exc.wait))
        return response


class DRFGenericErrorHandler(BaseExceptionHandler):
    """Fallback for every other DRF APIException and Django 404/403."""

    _CODES = {
        400: "bad_request",
        403: "permission_denied",
        404: "not_found",
        405: "method_not_allowed",
        415: "unsupported_media_type",
    }

    def can_handle(self, exc: Exception) -> bool:
        return isinstance(
            exc, (drf_exceptions.APIException, Http404, DjangoPermissionDenied)
        )

    def handle(self, exc: Exception, context: dict) -> ErrorResponse:
        if isinstance(exc, Http404):
            status_code, message = 404, "Resource not found."
        elif isinstance(exc, DjangoPermissionDenied):
            status_code, message = (
                403,
                "You do not have permission to perform this action.",
            )
        else:
            status_code, message = exc.status_code, str(exc.detail)
        return ErrorResponse(
            message=message,
            error_code=self._CODES.get(status_code, "error"),
            status_code=status_code,
        )


# Order matters: first handler that can_handle wins.
HANDLERS: tuple[BaseExceptionHandler, ...] = (
    AppExceptionHandler(),
    DRFValidationErrorHandler(),
    DRFAuthenticationErrorHandler(),
    DRFThrottledHandler(),
    DRFGenericErrorHandler(),
)


def exception_handler(exc: Exception, context: dict) -> Response | None:
    """DRF EXCEPTION_HANDLER. Returns None for unknown exceptions so Django
    produces its normal 500 (and Sentry sees it)."""
    for handler in HANDLERS:
        if handler.can_handle(exc):
            set_rollback()
            return handler.handle(exc, context)
    if isinstance(exc, AppException):  # pragma: no cover - covered above
        return None
    logger.exception("Unhandled exception in view", exc_info=exc)
    return None
