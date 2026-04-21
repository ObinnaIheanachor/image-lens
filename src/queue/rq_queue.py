from __future__ import annotations

from redis import Redis
from rq import Queue

from src.config import settings
from src.services.analysis import process_job


class RQQueue:
    def __init__(self) -> None:
        self._redis = Redis.from_url(settings.redis_url)
        self._queue = Queue(settings.rq_queue_name, connection=self._redis)

    def start(self) -> None:
        return

    def stop(self) -> None:
        return

    def enqueue(self, job_id: str) -> None:
        self._queue.enqueue(process_job, job_id, job_timeout=settings.job_timeout_seconds)

    def is_ready(self) -> bool:
        try:
            self._redis.ping()
            return True
        except Exception:
            return False

    def depth(self) -> int:
        return int(self._queue.count)


def create_worker() -> None:
    from rq import Worker
    redis_conn = Redis.from_url(settings.redis_url)
    worker = Worker([settings.rq_queue_name], connection=redis_conn)
    worker.work()
