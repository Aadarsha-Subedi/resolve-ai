from allauth.usersessions.models import UserSession
from django.contrib.auth import logout
from django.http import HttpRequest

from accounts.constants import errors, messages
from accounts.models import User
from accounts.services import hooks
from common.exception.domain import BadRequestException, NotFoundException


def list_sessions(user: User) -> list[UserSession]:
    """Live sessions of the user, newest activity first (dead rows are purged)."""
    sessions = UserSession.objects.purge_and_list(user)
    return sorted(sessions, key=lambda s: s.last_seen_at, reverse=True)


def revoke_session(request: HttpRequest, user: User, session_id: int) -> None:
    session = UserSession.objects.filter(user=user, pk=session_id).first()
    if session is None:
        raise NotFoundException(messages.MESSAGE_SESSION_NOT_FOUND)
    if session.session_key == request.session.session_key:
        raise BadRequestException(
            messages.MESSAGE_CANNOT_REVOKE_CURRENT,
            error_code=errors.ERROR_CANNOT_REVOKE_CURRENT,
        )
    session.end()
    hooks.emit(user, hooks.ACTION_SESSION_REVOKED)


def end_all_sessions(user: User) -> None:
    for session in UserSession.objects.filter(user=user):
        session.end()


def logout_current(request: HttpRequest) -> None:
    user = request.user
    logout(request)
    hooks.emit(user, hooks.ACTION_LOGOUT)


def logout_everywhere(request: HttpRequest) -> None:
    user = request.user
    end_all_sessions(user)
    logout(request)
    hooks.emit(user, hooks.ACTION_LOGOUT_ALL)
