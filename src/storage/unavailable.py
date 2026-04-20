from __future__ import annotations


class UnavailableObjectStore:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def put(self, data: bytes, suffix: str = ".jpg") -> tuple[str, str]:
        raise RuntimeError(f"object_store_unavailable: {self.reason}")

    def get(self, path: str) -> bytes:
        raise RuntimeError(f"object_store_unavailable: {self.reason}")

    def ready(self) -> bool:
        return False
