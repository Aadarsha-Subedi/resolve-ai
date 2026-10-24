from common.storage.base import FileStorage, ObjectInfo


class InMemoryStorage(FileStorage):
    """Concrete FileStorage for tests: keeps objects in a dict and fakes signed
    URLs. A test "uploads" through `simulate_browser_put`."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.presigned_puts: dict[str, tuple[str, int]] = {}

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def url(self, key: str) -> str:
        return f"https://files.test/{key}"

    def presign_put(
        self, key: str, content_type: str, size: int, expires_in: int
    ) -> str:
        self.presigned_puts[key] = (content_type, size)
        return f"https://files.test/put/{key}?expires={expires_in}"

    def presign_get(
        self,
        key: str,
        expires_in: int,
        filename: str | None = None,
        inline: bool = False,
    ) -> str:
        kind = "inline" if inline else "attachment"
        return f"https://files.test/get/{key}?disposition={kind}&filename={filename}"

    def head(self, key: str) -> ObjectInfo | None:
        if key not in self.objects:
            return None
        data, content_type = self.objects[key]
        return ObjectInfo(size=len(data), content_type=content_type)

    def read_range(self, key: str, length: int) -> bytes:
        return self.objects[key][0][:length]

    def read(self, key: str) -> bytes:
        return self.objects[key][0]

    def simulate_browser_put(self, key: str, data: bytes) -> None:
        """What the browser does with the signed URL: store the bytes under the
        content type that was signed."""
        content_type, _ = self.presigned_puts.get(key, ("", 0))
        self.objects[key] = (data, content_type)
