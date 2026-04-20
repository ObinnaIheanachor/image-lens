from __future__ import annotations

from src.config import settings
from src.queue.in_memory import InMemoryQueue


def create_queue() -> object:
    if settings.queue_backend == "rq":
        from src.queue.rq_queue import RQQueue

        return RQQueue()
    return InMemoryQueue()
