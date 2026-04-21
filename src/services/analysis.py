from __future__ import annotations

import json
import time

from src.analyzers.circuit_breaker import CircuitBreaker
from src.analyzers.factory import create_analyzer
from src.db.models import Job, Report
from src.db.session import get_session
from src.domain.errors import AnalyzerError
from src.services.ids import new_report_id
from src.services.webhook_dispatcher import dispatch_webhook
from src.storage.factory import create_object_store


_analyzer = create_analyzer()
_store = create_object_store()
_breaker = CircuitBreaker()


def process_job(job_id: str) -> str:
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if not job or job.status == "deleted":
            return "skipped"

        if not _breaker.allow():
            job.status = "failed"
            job.error_code = "analyzer_circuit_open"
            job.error_message = "Circuit breaker is open"
            session.commit()
            return "failed"

        job.status = "processing"
        job.attempt_count += 1
        job.error_code = None
        job.error_message = None
        session.commit()

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
                break
            except AnalyzerError as exc:
                last_exc = exc
                _breaker.record_failure()
                if exc.code == "analyzer_auth_failed":
                    raise
                if attempt < retries:
                    time.sleep(0.3 * (2**attempt))
            except Exception as exc:
                last_exc = exc
                _breaker.record_failure()
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
        session.commit()

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
                session.commit()

        return "done"

    except AnalyzerError as exc:
        job = session.get(Job, job_id)
        if not job:
            return "failed"
        job.status = "failed"
        job.error_code = exc.code
        job.error_message = exc.message
        session.commit()
        return "failed"
    except Exception as exc:
        job = session.get(Job, job_id)
        if not job:
            return "failed"
        job.status = "failed"
        job.error_code = "processing_failed"
        job.error_message = str(exc)
        session.commit()
        return "failed"
    finally:
        session.close()
