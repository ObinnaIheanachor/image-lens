from __future__ import annotations

import logging
import sys
import time
from typing import Callable

import structlog
from fastapi import Request, Response


_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            timestamper,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    _configured = True


async def log_http_access(request: Request, call_next: Callable) -> Response:
    logger = structlog.get_logger("http")
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    trace_id = getattr(request.state, "trace_id", "")
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=elapsed_ms,
        trace_id=trace_id,
    )
    return response
