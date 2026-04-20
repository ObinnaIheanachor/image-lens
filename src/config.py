import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "Image Insight"
    db_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./app.db"))
    storage_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("STORAGE_DIR", "./data/storage"))
    )


settings = Settings()
