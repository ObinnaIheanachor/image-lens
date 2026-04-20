from __future__ import annotations

import json

from src.analyzers.mock import MockAnalyzer
from src.db.models import Job, Report
from src.db.session import get_session
from src.services.ids import new_report_id
from src.services.webhook_dispatcher import dispatch_webhook
from src.storage.factory import create_object_store


_analyzer = MockAnalyzer()
_store = create_object_store()


def process_job(job_id: str) -> str:
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if not job or job.status == "deleted":
            return "skipped"

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

        result = _analyzer.analyze(image_bytes)
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
