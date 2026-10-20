from celery import shared_task

from knowledge.constants.settings import TASK_RELEASE_STALE_UPLOADS
from knowledge.services import upload_service


@shared_task(name=TASK_RELEASE_STALE_UPLOADS)
def release_stale_uploads() -> int:
    return upload_service.release_stale_uploads()
