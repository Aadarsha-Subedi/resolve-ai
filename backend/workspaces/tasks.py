from celery import shared_task

from workspaces.constants.settings import TASK_PURGE_DELETED_WORKSPACES
from workspaces.services import workspace_service


@shared_task(name=TASK_PURGE_DELETED_WORKSPACES)
def purge_deleted_workspaces() -> int:
    return workspace_service.purge_due_workspaces()
