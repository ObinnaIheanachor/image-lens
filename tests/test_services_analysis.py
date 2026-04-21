from __future__ import annotations

import json

import pytest

from src.db.models import Job, Report
from src.db.session import get_session
from src.domain.errors import AnalyzerError
from src.domain.schemas import AnalysisResult
from src.services.analysis import process_job


class _BreakerOpen:
    def allow(self) -> bool:
        return False

    def record_success(self) -> None:
        return

    def record_failure(self) -> None:
        return


class _BreakerClosed:
    def allow(self) -> bool:
        return True

    def record_success(self) -> None:
        return

    def record_failure(self) -> None:
        return


class _Store:
    def get(self, _path: str) -> bytes:
        return b"img-bytes"


class _AnalyzerOk:
    def analyze(self, _image_bytes: bytes, _mime: str) -> AnalysisResult:
        return AnalysisResult(
            summary="ok",
            tags=["unit"],
            confidence=0.95,
            analyzer_version="unit-test",
        )


def _seed_job(
    *,
    job_id: str,
    status: str = "queued",
    webhook_url: str | None = None,
    metadata: dict | None = None,
    attempt_count: int = 0,
) -> None:
    session = get_session()
    try:
        job = Job(
            id=job_id,
            status=status,
            image_path=f"/tmp/{job_id}.jpg",
            image_sha256="a" * 64,
            image_mime="image/jpeg",
            image_bytes=10,
            image_width=1,
            image_height=1,
            idempotency_key=None,
            webhook_url=webhook_url,
            user_metadata_json=json.dumps(metadata or {}),
            report_id=None,
            error_code=None,
            error_message=None,
            attempt_count=attempt_count,
        )
        session.add(job)
        session.commit()
    finally:
        session.close()


def _load_job(job_id: str) -> Job:
    session = get_session()
    try:
        job = session.get(Job, job_id)
        assert job is not None
        session.expunge(job)
        return job
    finally:
        session.close()


def _load_report(report_id: str) -> Report:
    session = get_session()
    try:
        report = session.get(Report, report_id)
        assert report is not None
        session.expunge(report)
        return report
    finally:
        session.close()


def test_process_job_skips_missing_and_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.services.analysis._breaker", _BreakerClosed())
    monkeypatch.setattr("src.services.analysis._store", _Store())
    monkeypatch.setattr("src.services.analysis._analyzer", _AnalyzerOk())

    assert process_job("job_missing") == "skipped"

    _seed_job(job_id="job_deleted", status="deleted")
    assert process_job("job_deleted") == "skipped"


def test_process_job_marks_circuit_open(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_job(job_id="job_circuit")
    monkeypatch.setattr("src.services.analysis._breaker", _BreakerOpen())
    monkeypatch.setattr("src.services.analysis._store", _Store())
    monkeypatch.setattr("src.services.analysis._analyzer", _AnalyzerOk())

    out = process_job("job_circuit")
    assert out == "failed"
    job = _load_job("job_circuit")
    assert job.status == "failed"
    assert job.error_code == "analyzer_circuit_open"


def test_process_job_succeeds_and_persists_report(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_job(job_id="job_ok")
    monkeypatch.setattr("src.services.analysis._breaker", _BreakerClosed())
    monkeypatch.setattr("src.services.analysis._store", _Store())
    monkeypatch.setattr("src.services.analysis._analyzer", _AnalyzerOk())
    monkeypatch.setattr("src.services.analysis.new_report_id", lambda: "rpt_unit_ok")
    monkeypatch.setattr("src.services.analysis.dispatch_webhook", lambda _u, _p: (True, None))

    out = process_job("job_ok")
    assert out == "done"

    job = _load_job("job_ok")
    assert job.status == "done"
    assert job.report_id == "rpt_unit_ok"

    report = _load_report("rpt_unit_ok")
    payload = json.loads(report.payload_json or "{}")
    assert payload["summary"] == "ok"
    assert payload["analyzer_version"] == "unit-test"


def test_process_job_sets_webhook_failure_without_failing_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_job(job_id="job_wh", webhook_url="http://example.com/hook")
    monkeypatch.setattr("src.services.analysis._breaker", _BreakerClosed())
    monkeypatch.setattr("src.services.analysis._store", _Store())
    monkeypatch.setattr("src.services.analysis._analyzer", _AnalyzerOk())
    monkeypatch.setattr("src.services.analysis.new_report_id", lambda: "rpt_unit_wh")
    monkeypatch.setattr(
        "src.services.analysis.dispatch_webhook",
        lambda _u, _p: (False, "timeout"),
    )

    out = process_job("job_wh")
    assert out == "done"
    job = _load_job("job_wh")
    assert job.status == "done"
    assert job.error_code == "webhook_delivery_failed"
    assert job.error_message == "timeout"


def test_process_job_retries_then_fails_with_analyzer_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_job(job_id="job_retry_fail")
    monkeypatch.setattr("src.services.analysis._breaker", _BreakerClosed())
    monkeypatch.setattr("src.services.analysis._store", _Store())
    monkeypatch.setattr("src.services.analysis.time.sleep", lambda _s: None)

    class _AnalyzerAlwaysError:
        def analyze(self, _image_bytes: bytes, _mime: str) -> AnalysisResult:
            raise AnalyzerError("analyzer_upstream_error", "boom", status_code=502)

    monkeypatch.setattr("src.services.analysis._analyzer", _AnalyzerAlwaysError())

    out = process_job("job_retry_fail")
    assert out == "failed"
    job = _load_job("job_retry_fail")
    assert job.status == "failed"
    assert job.error_code == "analyzer_upstream_error"
    assert job.error_message == "boom"


def test_process_job_auth_failure_and_force_fail_once(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_job(job_id="job_auth_fail")
    _seed_job(job_id="job_force", metadata={"force_fail_once": True})
    monkeypatch.setattr("src.services.analysis._breaker", _BreakerClosed())
    monkeypatch.setattr("src.services.analysis._store", _Store())
    monkeypatch.setattr("src.services.analysis.time.sleep", lambda _s: None)

    class _AnalyzerAuthFail:
        def analyze(self, _image_bytes: bytes, _mime: str) -> AnalysisResult:
            raise AnalyzerError("analyzer_auth_failed", "bad key", status_code=401)

    monkeypatch.setattr("src.services.analysis._analyzer", _AnalyzerAuthFail())
    assert process_job("job_auth_fail") == "failed"
    auth_job = _load_job("job_auth_fail")
    assert auth_job.error_code == "analyzer_auth_failed"

    # Generic runtime failure path maps to processing_failed.
    monkeypatch.setattr("src.services.analysis._analyzer", _AnalyzerOk())
    assert process_job("job_force") == "failed"
    forced = _load_job("job_force")
    assert forced.error_code == "processing_failed"
    assert forced.error_message == "forced_fail_once"
