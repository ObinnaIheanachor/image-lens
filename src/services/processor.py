from __future__ import annotations

import json
import queue
import threading
import time

from src.analyzers.mock import MockAnalyzer
from src.db.models import Job, Report
from src.db.session import get_session
from src.services.ids import new_report_id
from src.storage.local import LocalStore


class JobProcessor:
    def __init__(self) -> None:
        self._q: queue.Queue[str] = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None
        self._analyzer = MockAnalyzer()
        self._store = LocalStore()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def enqueue(self, job_id: str) -> None:
        self._q.put(job_id)

    def _loop(self) -> None:
        while self._running:
            try:
                job_id = self._q.get(timeout=0.2)
            except queue.Empty:
                continue

            session = get_session()
            try:
                job = session.get(Job, job_id)
                if not job:
                    continue
                job.status = "processing"
                job.attempt_count += 1
                session.commit()

                image_bytes = self._store.get(job.image_path)
                result = self._analyzer.analyze(image_bytes)
                report_id = new_report_id()
                report = Report(
                    id=report_id,
                    job_id=job.id,
                    payload_json=json.dumps(result.model_dump()),
                )
                session.add(report)

                job.status = "done"
                job.report_id = report_id
                job.error_code = None
                job.error_message = None
                session.commit()
            except Exception as exc:  # pragma: no cover - thin slice recovery
                job = session.get(Job, job_id)
                if job:
                    job.status = "failed"
                    job.error_code = "processing_failed"
                    job.error_message = str(exc)
                    session.commit()
            finally:
                session.close()
                time.sleep(0.1)


processor = JobProcessor()
