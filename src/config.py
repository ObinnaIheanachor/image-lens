from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "Image Insight"
    api_key: str = Field(default_factory=lambda: os.getenv("API_KEY", "changeme-before-deploy"))
    ai_provider: str = Field(default_factory=lambda: os.getenv("AI_PROVIDER", "mock"))
    anthropic_api_key: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    claude_model: str = Field(
        default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    )

    db_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./app.db"))
    storage_dir: Path = Field(default_factory=lambda: Path(os.getenv("STORAGE_DIR", "./data/storage")))

    queue_backend: str = Field(default_factory=lambda: os.getenv("QUEUE_BACKEND", "inmemory"))
    inmemory_queue_inline: bool = Field(
        default_factory=lambda: os.getenv("INMEMORY_QUEUE_INLINE", "false").lower() == "true"
    )
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
    rate_limit_enabled: bool = Field(default_factory=lambda: os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true")
    rate_limit_uploads_per_minute: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_UPLOADS_PER_MINUTE", "60"))
    )
    max_upload_size_bytes: int = Field(
        default_factory=lambda: int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(20 * 1024 * 1024)))
    )
    max_image_width: int = Field(default_factory=lambda: int(os.getenv("MAX_IMAGE_WIDTH", "10000")))
    max_image_height: int = Field(default_factory=lambda: int(os.getenv("MAX_IMAGE_HEIGHT", "10000")))
    enable_sweepers: bool = Field(default_factory=lambda: os.getenv("ENABLE_SWEEPERS", "true").lower() == "true")
    sweep_interval_seconds: int = Field(default_factory=lambda: int(os.getenv("SWEEP_INTERVAL_SECONDS", "60")))
    stuck_job_timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("STUCK_JOB_TIMEOUT_SECONDS", "300"))
    )
    retention_hard_delete_days: int = Field(
        default_factory=lambda: int(os.getenv("RETENTION_HARD_DELETE_DAYS", "30"))
    )

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
