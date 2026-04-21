from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

# Ensure settings pick test-safe defaults before app import.
os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["STORAGE_DIR"] = "./data/test-storage"
os.environ["QUEUE_BACKEND"] = "inmemory"
os.environ["INMEMORY_QUEUE_INLINE"] = "true"
os.environ["OBJECT_STORE_BACKEND"] = "local"
os.environ["API_KEY"] = "test-api-key"
os.environ["ENABLE_SWEEPERS"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["RATE_LIMIT_UPLOADS_PER_MINUTE"] = "1000"

from src.db.models import Job, Report
from src.db.session import get_session, init_db
from src.main import app


@pytest.fixture(autouse=True)
def clean_state() -> None:
    # Prevent queue thread races while resetting SQLite-backed test state.
    from src.api.routes import queue_backend

    queue_backend.stop()
    init_db()

    session = get_session()
    try:
        session.query(Report).delete()
        session.query(Job).delete()
        session.commit()
    finally:
        session.close()

    storage_dir = Path(os.environ["STORAGE_DIR"])
    if storage_dir.exists():
        shutil.rmtree(storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
