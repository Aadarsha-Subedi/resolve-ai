from typing import Any

from common.logger.redaction import redact_sensitive_data
from common.logger.request_id import current_request_id


def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    """Last line of defence before an event leaves the server: redact secrets
    in whatever request data or extras are attached and add the request id."""
    request = event.get("request")
    if isinstance(request, dict):
        for key in ("data", "headers", "cookies", "query_string"):
            if key in request:
                request[key] = redact_sensitive_data(request[key])
        request.pop("cookies", None)
    for key in ("extra", "contexts"):
        if isinstance(event.get(key), dict):
            event[key] = redact_sensitive_data(event[key])
    request_id = current_request_id()
    if request_id:
        event.setdefault("tags", {})
        if isinstance(event["tags"], dict):
            event["tags"].setdefault("request_id", request_id)
    return event
