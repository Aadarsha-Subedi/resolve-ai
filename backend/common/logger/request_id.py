"""Request correlation: one id per request, visible in every log line, in the
`X-Request-ID` response header, in Sentry events and in Celery tasks started
by the request."""

import logging
import re
import uuid
from collections.abc import Callable
from contextvars import ContextVar

import sentry_sdk
from django.http import HttpRequest, HttpResponse

REQUEST_ID_HEADER = "X-Request-ID"
CELERY_HEADER = "request_id"
_VALID_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def current_request_id() -> str | None:
    return request_id_var.get()


def new_request_id() -> str:
    return uuid.uuid4().hex


def accept_request_id(candidate: str | None) -> str:
    """Use the caller's id only when it looks like one, otherwise make our own
    (so a client cannot inject odd characters into logs)."""
    if candidate and _VALID_ID.match(candidate):
        return candidate
    return new_request_id()


class RequestIdFilter(logging.Filter):
    """Stamps every log record with the current request and user ids."""

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "request_id", None) is None:
            record.request_id = request_id_var.get()
        if getattr(record, "user_id", None) is None:
            record.user_id = user_id_var.get()
        return True


class RequestIdMiddleware:
    """First middleware: assigns the id, echoes it on the response and clears
    the context afterwards."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = accept_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.request_id = request_id
        id_token = request_id_var.set(request_id)
        user_token = user_id_var.set(None)
        sentry_sdk.set_tag("request_id", request_id)
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(id_token)
            user_id_var.reset(user_token)
        response[REQUEST_ID_HEADER] = request_id
        return response


class UserContextMiddleware:
    """After authentication: remembers who the request is for, in the logs and
    in Sentry (user id only, never email or IP)."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            user_id = str(user.pk)
            user_id_var.set(user_id)
            sentry_sdk.set_user({"id": user_id})
        return self.get_response(request)


def connect_celery() -> None:
    """Carry the request id into tasks started by a request and restore it in
    the worker, so one id follows the work end to end."""
    from celery.signals import before_task_publish, task_postrun, task_prerun

    @before_task_publish.connect(weak=False)
    def add_request_id(headers=None, **kwargs):
        request_id = request_id_var.get()
        if request_id and headers is not None:
            headers.setdefault(CELERY_HEADER, request_id)

    @task_prerun.connect(weak=False)
    def restore_request_id(task=None, **kwargs):
        request_id = getattr(task.request, CELERY_HEADER, None) if task else None
        if request_id:
            task.request._request_id_token = request_id_var.set(request_id)

    @task_postrun.connect(weak=False)
    def clear_request_id(task=None, **kwargs):
        token = getattr(task.request, "_request_id_token", None) if task else None
        if token is not None:
            request_id_var.reset(token)
