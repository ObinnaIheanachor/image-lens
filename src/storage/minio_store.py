from __future__ import annotations

import hashlib
from io import BytesIO

from minio import Minio

from src.config import settings


class MinioObjectStore:
    def __init__(self) -> None:
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._bucket = settings.minio_bucket
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def put(self, data: bytes, suffix: str = ".jpg") -> tuple[str, str]:
        digest = hashlib.sha256(data).hexdigest()
        key = f"{digest}{suffix}"
        self._client.put_object(
            self._bucket,
            key,
            BytesIO(data),
            length=len(data),
            content_type="image/jpeg",
        )
        return digest, key

    def get(self, path: str) -> bytes:
        response = self._client.get_object(self._bucket, path)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def ready(self) -> bool:
        try:
            self._client.bucket_exists(self._bucket)
            return True
        except Exception:
            return False
