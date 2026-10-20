# Load the Celery app when Django starts so @shared_task uses it (and its settings,
# including eager mode in tests).
from config.celery import app as celery_app

__all__ = ["celery_app"]
