from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.db.models import Base


engine = create_engine(settings.db_url, future=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False)


_REQUIRED_JOB_COLUMNS = {
    "id",
    "status",
    "image_path",
    "image_sha256",
    "image_mime",
    "idempotency_key",
    "webhook_url",
    "user_metadata_json",
    "report_id",
    "error_code",
    "error_message",
    "attempt_count",
    "created_at",
    "updated_at",
}


def _sqlite_schema_compatible() -> bool:
    if not settings.db_url.startswith("sqlite"):
        return True
    insp = inspect(engine)
    if "jobs" not in insp.get_table_names():
        return True
    cols = {c["name"] for c in insp.get_columns("jobs")}
    return _REQUIRED_JOB_COLUMNS.issubset(cols)


def init_db() -> None:
    if not _sqlite_schema_compatible():
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _ensure_job_schema()


def _ensure_job_schema() -> None:
    insp = inspect(engine)
    if "jobs" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("jobs")}
    missing_defs = []
    if "idempotency_key" not in cols:
        missing_defs.append(("idempotency_key", "TEXT"))

    if not missing_defs:
        return

    with engine.begin() as conn:
        for col_name, col_type in missing_defs:
            conn.execute(text(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}"))


def get_session() -> Session:
    return SessionLocal()


def db_ready() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
