from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.config import settings
from src.db.models import Job, Report
from src.db.session import get_session
from src.services.sweepers import run_retention_sweeper, run_stuck_job_reconciler


def test_stuck_job_reconciler_marks_processing_jobs_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "stuck_job_timeout_seconds", 300)
    now = datetime.now(UTC)
    stale = now - timedelta(seconds=600)

    session = get_session()
    try:
        job = Job(
            id="job_stuck_1",
            status="processing",
            image_path="./data/test-storage/stuck.jpg",
            image_sha256="1" * 64,
            image_mime="image/jpeg",
            image_bytes=1,
            image_width=1,
            image_height=1,
            idempotency_key=None,
            webhook_url=None,
            user_metadata_json="{}",
            report_id=None,
            error_code=None,
            error_message=None,
            attempt_count=1,
            created_at=stale,
            updated_at=stale,
        )
        session.add(job)
        session.commit()
    finally:
        session.close()

    updated = run_stuck_job_reconciler(now=now)
    assert updated == 1

    session = get_session()
    try:
        got = session.get(Job, "job_stuck_1")
        assert got is not None
        assert got.status == "failed"
        assert got.error_code == "stuck_job_timeout"
    finally:
        session.close()


def test_retention_sweeper_hard_deletes_old_deleted_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "retention_hard_delete_days", 30)
    now = datetime.now(UTC)
    stale = now - timedelta(days=45)

    storage_path = Path("./data/test-storage/old.jpg")
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(b"abc")

    session = get_session()
    try:
        report = Report(
            id="rpt_old_1",
            job_id="job_old_1",
            payload_json='{"summary":"old"}',
            created_at=stale,
        )
        job = Job(
            id="job_old_1",
            status="deleted",
            image_path=str(storage_path),
            image_sha256="2" * 64,
            image_mime="image/jpeg",
            image_bytes=1,
            image_width=1,
            image_height=1,
            idempotency_key=None,
            webhook_url=None,
            user_metadata_json="{}",
            report_id=report.id,
            error_code=None,
            error_message=None,
            attempt_count=1,
            created_at=stale,
            updated_at=stale,
        )
        session.add(report)
        session.add(job)
        session.commit()
    finally:
        session.close()

    deleted = run_retention_sweeper(now=now)
    assert deleted == 1

    session = get_session()
    try:
        assert session.get(Job, "job_old_1") is None
        assert session.get(Report, "rpt_old_1") is None
    finally:
        session.close()

    assert not storage_path.exists()
