from __future__ import annotations

import hashlib
from pathlib import Path

from src.config import settings


class LocalStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or settings.storage_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes, suffix: str = ".jpg") -> tuple[str, str]:
        digest = hashlib.sha256(data).hexdigest()
        path = self.base_dir / f"{digest}{suffix}"
        if not path.exists():
            path.write_bytes(data)
        return digest, str(path)

    def get(self, path: str) -> bytes:
        return Path(path).read_bytes()

    def ready(self) -> bool:
        return self.base_dir.exists() and self.base_dir.is_dir()
