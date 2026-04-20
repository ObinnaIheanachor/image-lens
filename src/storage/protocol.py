from __future__ import annotations

from typing import Protocol


class ObjectStore(Protocol):
    def put(self, data: bytes, suffix: str = ".jpg") -> tuple[str, str]:
        ...

    def get(self, path: str) -> bytes:
        ...

    def ready(self) -> bool:
        ...
