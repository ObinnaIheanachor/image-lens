from __future__ import annotations

from src.config import settings
from src.storage.local import LocalStore
from src.storage.unavailable import UnavailableObjectStore


def create_object_store() -> object:
    if settings.object_store_backend == "minio":
        try:
            from src.storage.minio_store import MinioObjectStore

            return MinioObjectStore()
        except Exception as exc:
            return UnavailableObjectStore(str(exc))
    return LocalStore()
