from __future__ import annotations

import queue
import threading
import time

from src.config import settings
from src.services.analysis import process_job


class InMemoryQueue:
    def __init__(self) -> None:
        self._q: queue.Queue[str] = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join()

    def enqueue(self, job_id: str) -> None:
        if settings.inmemory_queue_inline:
            process_job(job_id)
            return
        self._q.put(job_id)

    def is_ready(self) -> bool:
        return True

    def _loop(self) -> None:
        while self._running:
            try:
                job_id = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            process_job(job_id)
            time.sleep(0.05)
