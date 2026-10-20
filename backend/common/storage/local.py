from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage

from common.storage.base import DirectUploadUnsupported, FileStorage, ObjectInfo


class LocalFileStorage(FileStorage):
    """Concrete FileStorage for local development (files under MEDIA_ROOT)."""

    def __init__(self) -> None:
        self._storage = FileSystemStorage(location=settings.MEDIA_ROOT)

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        if self._storage.exists(key):
            self._storage.delete(key)
        self._storage.save(key, ContentFile(data))

    def delete(self, key: str) -> None:
        self._storage.delete(key)

    def url(self, key: str) -> str:
        return f"/{settings.MEDIA_URL.strip('/')}/{key}"

    def presign_put(
        self, key: str, content_type: str, size: int, expires_in: int
    ) -> str:
        raise DirectUploadUnsupported

    def presign_get(
        self,
        key: str,
        expires_in: int,
        filename: str | None = None,
        inline: bool = False,
    ) -> str:
        raise DirectUploadUnsupported

    def head(self, key: str) -> ObjectInfo | None:
        if not self._storage.exists(key):
            return None
        return ObjectInfo(size=self._storage.size(key), content_type="")

    def read_range(self, key: str, length: int) -> bytes:
        with self._storage.open(key) as handle:
            return handle.read(length)

    def read(self, key: str) -> bytes:
        with self._storage.open(key) as handle:
            return handle.read()
