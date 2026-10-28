from celery import shared_task

from ai.constants.settings import TASK_PURGE_USAGE_LOGS
from ai.services import usage_service


@shared_task(name=TASK_PURGE_USAGE_LOGS)
def purge_usage_logs() -> int:
    return usage_service.purge_old()
