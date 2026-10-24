from functools import lru_cache

from django.conf import settings

from common.storage.base import FileStorage


@lru_cache(maxsize=1)
def get_storage() -> FileStorage:
    """Composition root for file storage: R2 when configured, local disk otherwise."""
    if settings.R2_BUCKET_NAME:
        from common.storage.r2 import R2Storage

        return R2Storage()

    from common.storage.local import LocalFileStorage

    return LocalFileStorage()
