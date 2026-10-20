import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from django.conf import settings

from common.storage.base import FileStorage, ObjectInfo


class R2Storage(FileStorage):
    """Concrete FileStorage for Cloudflare R2 (S3 compatible) through boto3."""

    def __init__(self) -> None:
        self._client: BaseClient | None = None

    @property
    def client(self) -> BaseClient:
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name="auto",
            )
        return self._client

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=settings.R2_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key)

    def url(self, key: str) -> str:
        return f"{settings.R2_PUBLIC_BASE_URL.rstrip('/')}/{key}"

    def presign_put(
        self, key: str, content_type: str, size: int, expires_in: int
    ) -> str:
        # Content-Length and Content-Type are part of the signature, so the
        # browser must send exactly what was declared.
        return self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.R2_BUCKET_NAME,
                "Key": key,
                "ContentType": content_type,
                "ContentLength": size,
            },
            ExpiresIn=expires_in,
        )

    def presign_get(
        self,
        key: str,
        expires_in: int,
        filename: str | None = None,
        inline: bool = False,
    ) -> str:
        params = {"Bucket": settings.R2_BUCKET_NAME, "Key": key}
        if filename:
            kind = "inline" if inline else "attachment"
            safe = filename.replace('"', "")
            params["ResponseContentDisposition"] = f'{kind}; filename="{safe}"'
        return self.client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expires_in
        )

    def head(self, key: str) -> ObjectInfo | None:
        try:
            result = self.client.head_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in (
                "404",
                "NoSuchKey",
                "NotFound",
            ):
                return None
            raise
        return ObjectInfo(
            size=result["ContentLength"], content_type=result.get("ContentType", "")
        )

    def read_range(self, key: str, length: int) -> bytes:
        result = self.client.get_object(
            Bucket=settings.R2_BUCKET_NAME, Key=key, Range=f"bytes=0-{length - 1}"
        )
        return result["Body"].read()

    def read(self, key: str) -> bytes:
        result = self.client.get_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
        return result["Body"].read()
