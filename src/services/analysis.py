from __future__ import annotations

import json
import time

from sqlalchemy.orm.exc import StaleDataError

from src.analyzers.circuit_breaker import CircuitBreaker
from src.analyzers.factory import create_analyzer
from src.db.models import Job, Report
from src.db.session import get_session
from src.domain.errors import AnalyzerError
from src.observability.metrics import (
    ANALYSIS_DURATION_SECONDS,
    ANALYSIS_FAILURES_TOTAL,
    CIRCUIT_BREAKER_STATE,
    refresh_jobs_in_flight,
)
from src.services.ids import new_report_id
from src.services.webhook_dispatcher import dispatch_webhook
from src.storage.factory import create_object_store


_analyzer = create_analyzer()
_store = create_object_store()
_breaker = CircuitBreaker()


def _set_breaker_state() -> None:
    opened_at = getattr(_breaker, "opened_at", None)
    state = 2 if opened_at is not None else 0
    CIRCUIT_BREAKER_STATE.labels(analyzer="default").set(state)


_set_breaker_state()


def _commit_or_recover(session, job_id: str) -> bool:
    try:
        session.commit()
        return True
    except StaleDataError:
        session.rollback()
        return session.get(Job, job_id) is not None


def process_job(job_id: str) -> str:
    started_at = time.perf_counter()
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if not job or job.status == "deleted":
            refresh_jobs_in_flight()
            return "skipped"

        if not _breaker.allow():
            job.status = "failed"
            job.error_code = "analyzer_circuit_open"
            job.error_message = "Circuit breaker is open"
            session.commit()
            ANALYSIS_FAILURES_TOTAL.labels(reason="analyzer_circuit_open").inc()
            _set_breaker_state()
            refresh_jobs_in_flight()
            return "failed"

        job.status = "processing"
        job.attempt_count += 1
        job.error_code = None
        job.error_message = None
        if not _commit_or_recover(session, job_id):
            refresh_jobs_in_flight()
            return "skipped"

        image_bytes = _store.get(job.image_path)

        metadata = job.user_metadata_json or "{}"
        meta_obj = json.loads(metadata)
        if meta_obj.get("force_fail_once") and job.attempt_count == 1:
            raise RuntimeError("forced_fail_once")

        retries = 2
        last_exc: Exception | None = None
        result = None
        for attempt in range(retries + 1):
            try:
                result = _analyzer.analyze(image_bytes, job.image_mime)
                _breaker.record_success()
                _set_breaker_state()
                break
            except AnalyzerError as exc:
                last_exc = exc
                _breaker.record_failure()
                _set_breaker_state()
                if exc.code == "analyzer_auth_failed":
                    raise
                if attempt < retries:
                    time.sleep(0.3 * (2**attempt))
            except Exception as exc:
                last_exc = exc
                _breaker.record_failure()
                _set_breaker_state()
                if attempt < retries:
                    time.sleep(0.3 * (2**attempt))

        if result is None:
            if isinstance(last_exc, AnalyzerError):
                raise last_exc
            raise RuntimeError(str(last_exc) if last_exc else "analyzer_failed")

        report_id = new_report_id()
        report_obj = result.model_dump()
        report = Report(
            id=report_id,
            job_id=job.id,
            payload_json=json.dumps(report_obj),
        )
        session.add(report)

        job.status = "done"
        job.report_id = report_id
        if not _commit_or_recover(session, job_id):
            refresh_jobs_in_flight()
            return "failed"

        if job.webhook_url:
            payload = {
                "job_id": job.id,
                "report_id": report_id,
                "status": "done",
                "report": report_obj,
            }
            ok, error = dispatch_webhook(job.webhook_url, payload)
            if not ok:
                job.error_code = "webhook_delivery_failed"
                job.error_message = error
                _commit_or_recover(session, job_id)

        ANALYSIS_DURATION_SECONDS.observe(max(time.perf_counter() - started_at, 0.0))
        refresh_jobs_in_flight()
        return "done"

    except AnalyzerError as exc:
        session.rollback()
        job = session.get(Job, job_id)
        if not job:
            ANALYSIS_FAILURES_TOTAL.labels(reason=exc.code).inc()
            ANALYSIS_DURATION_SECONDS.observe(max(time.perf_counter() - started_at, 0.0))
            refresh_jobs_in_flight()
            return "failed"
        job.status = "failed"
        job.error_code = exc.code
        job.error_message = exc.message
        _commit_or_recover(session, job_id)
        ANALYSIS_FAILURES_TOTAL.labels(reason=exc.code).inc()
        ANALYSIS_DURATION_SECONDS.observe(max(time.perf_counter() - started_at, 0.0))
        refresh_jobs_in_flight()
        return "failed"
    except Exception as exc:
        session.rollback()
        job = session.get(Job, job_id)
        if not job:
            ANALYSIS_FAILURES_TOTAL.labels(reason="processing_failed").inc()
            ANALYSIS_DURATION_SECONDS.observe(max(time.perf_counter() - started_at, 0.0))
            refresh_jobs_in_flight()
            return "failed"
        job.status = "failed"
        job.error_code = "processing_failed"
        job.error_message = str(exc)
        _commit_or_recover(session, job_id)
        ANALYSIS_FAILURES_TOTAL.labels(reason="processing_failed").inc()
        ANALYSIS_DURATION_SECONDS.observe(max(time.perf_counter() - started_at, 0.0))
        refresh_jobs_in_flight()
        return "failed"
    finally:
        session.close()
