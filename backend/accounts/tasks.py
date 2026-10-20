from celery import shared_task
from django.core.management import call_command

from accounts.constants.settings import (
    SESSION_PURGE_BATCH_SIZE,
    TASK_CLEAR_EXPIRED_SESSIONS,
    TASK_PURGE_DELETED_ACCOUNTS,
)
from accounts.services import deletion_service


@shared_task(name=TASK_PURGE_DELETED_ACCOUNTS)
def purge_deleted_accounts() -> int:
    return deletion_service.purge_due_accounts()


@shared_task(name=TASK_CLEAR_EXPIRED_SESSIONS)
def clear_expired_sessions() -> int:
    """Delete expired Django sessions, then the device rows whose session is gone."""
    from allauth.usersessions.models import UserSession

    call_command("clearsessions")
    purged = 0
    for session in UserSession.objects.all().iterator(
        chunk_size=SESSION_PURGE_BATCH_SIZE
    ):
        if session.purge():
            purged += 1
    return purged
