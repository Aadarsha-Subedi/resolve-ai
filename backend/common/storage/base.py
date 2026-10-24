from abc import ABC, abstractmethod
from dataclasses import dataclass


class DirectUploadUnsupported(Exception):
    """The configured storage cannot hand out signed URLs (local disk)."""


@dataclass(frozen=True)
class ObjectInfo:
    """What the storage reports about a stored object."""

    size: int
    content_type: str


class FileStorage(ABC):
    """Role: abstraction over where uploaded files live (R2, local disk).
    Clients depend on this; the concrete class is picked in `get_storage`."""

    @abstractmethod
    def upload(self, key: str, data: bytes, content_type: str) -> None:
        """Store `data` under `key`."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove `key`. Missing keys are ignored."""

    @abstractmethod
    def url(self, key: str) -> str:
        """Public URL for `key`."""

    @abstractmethod
    def presign_put(
        self, key: str, content_type: str, size: int, expires_in: int
    ) -> str:
        """Signed URL the browser can PUT exactly `size` bytes of
        `content_type` to. Raises DirectUploadUnsupported if not available."""

    @abstractmethod
    def presign_get(
        self,
        key: str,
        expires_in: int,
        filename: str | None = None,
        inline: bool = False,
    ) -> str:
        """Signed URL to read `key`. `filename` and `inline` set the download
        headers (forced download unless `inline`)."""

    @abstractmethod
    def head(self, key: str) -> ObjectInfo | None:
        """Size and content type of `key`, or None if it does not exist."""

    @abstractmethod
    def read_range(self, key: str, length: int) -> bytes:
        """The first `length` bytes of `key`."""

    @abstractmethod
    def read(self, key: str) -> bytes:
        """The whole object."""
