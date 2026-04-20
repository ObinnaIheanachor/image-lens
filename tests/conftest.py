from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure settings pick test-safe defaults before app import.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_app.db")
os.environ.setdefault("STORAGE_DIR", "./data/test-storage")
os.environ.setdefault("QUEUE_BACKEND", "inmemory")
os.environ.setdefault("OBJECT_STORE_BACKEND", "local")
os.environ.setdefault("API_KEY", "test-api-key")

from src.db.models import Job, Report
from src.db.session import get_session, init_db
from src.main import app


@pytest.fixture(autouse=True)
def clean_state() -> None:
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
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
