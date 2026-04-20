from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "Image Insight"
    api_key: str = Field(default_factory=lambda: os.getenv("API_KEY", "changeme-before-deploy"))

    db_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./app.db"))
    storage_dir: Path = Field(default_factory=lambda: Path(os.getenv("STORAGE_DIR", "./data/storage")))

    queue_backend: str = Field(default_factory=lambda: os.getenv("QUEUE_BACKEND", "inmemory"))
    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    rq_queue_name: str = Field(default_factory=lambda: os.getenv("RQ_QUEUE_NAME", "image-insight"))

    object_store_backend: str = Field(default_factory=lambda: os.getenv("OBJECT_STORE_BACKEND", "local"))
    minio_endpoint: str = Field(default_factory=lambda: os.getenv("MINIO_ENDPOINT", "localhost:9000"))
    minio_access_key: str = Field(default_factory=lambda: os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
    minio_secret_key: str = Field(default_factory=lambda: os.getenv("MINIO_SECRET_KEY", "minioadmin"))
    minio_bucket: str = Field(default_factory=lambda: os.getenv("MINIO_BUCKET", "image-insight"))
    minio_secure: bool = Field(default_factory=lambda: os.getenv("MINIO_SECURE", "false").lower() == "true")

    job_timeout_seconds: int = Field(default_factory=lambda: int(os.getenv("JOB_TIMEOUT_SECONDS", "60")))
    webhook_timeout_seconds: int = Field(default_factory=lambda: int(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "3")))
    allow_private_webhooks: bool = Field(default_factory=lambda: os.getenv("ALLOW_PRIVATE_WEBHOOKS", "true").lower() == "true")

    cors_origins_raw: str = Field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


settings = Settings()
