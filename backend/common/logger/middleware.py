import json
import logging
import time

from common.logger.redaction import redact_sensitive_data

logger = logging.getLogger("request")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def get_view_name(self, request) -> str | None:
        return (
            getattr(request.resolver_match, "view_name", None)
            if request.resolver_match
            else None
        )

    def get_request_body(self, request) -> dict | None:

        if request.content_type.startswith("multipart/"):
            return {"raw": "<multipart body>"}

        if not request.body:
            return None

        try:
            return json.loads(request.body)
        except json.JSONDecodeError, UnicodeDecodeError:
            return {"raw": "<non-JSON body>"}

    def get_response_body(self, response) -> dict | None:

        if not hasattr(response, "data"):
            return None

        return (
            redact_sensitive_data(response.data)
            if isinstance(response.data, (dict, list))
            else response.data
        )

    def __call__(self, request):
        start = time.monotonic()

        request_body = self.get_request_body(request)

        response = self.get_response(request)

        duration_ms = round((time.monotonic() - start) * 1000, 2)

        log_data = {
            "method": request.method,
            "route": request.path,
            "view_name": self.get_view_name(request),
            "query_params": redact_sensitive_data(dict(request.GET)),
            "headers": redact_sensitive_data(dict(request.headers)),
            "body": redact_sensitive_data(request_body),
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "response_body": self.get_response_body(response),
        }

        level = logging.ERROR if response.status_code >= 400 else logging.INFO

        logger.log(
            level,
            "Request handled",
            extra={
                "request_data": log_data,
                "request_id": getattr(request, "request_id", None),
            },
        )

        return response
