from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from src.db.models import Job
from src.db.session import get_session

HTTP_REQUESTS_TOTAL = Counter(
    "image_insight_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "image_insight_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)
UPLOADS_TOTAL = Counter(
    "image_insight_uploads_total",
    "Total upload requests",
    ["mode"],
)
JOBS_RETRY_TOTAL = Counter(
    "image_insight_jobs_retry_total",
    "Total retry requests",
)
ANALYSIS_DURATION_SECONDS = Histogram(
    "image_intel_analysis_duration_seconds",
    "Image analysis duration in seconds",
)
ANALYSIS_FAILURES_TOTAL = Counter(
    "image_intel_analysis_failures_total",
    "Total image analysis failures",
    ["reason"],
)
QUEUE_DEPTH = Gauge(
    "image_intel_queue_depth",
    "Current queue depth",
    ["queue"],
)
JOBS_IN_FLIGHT = Gauge(
    "image_intel_jobs_in_flight",
    "Number of jobs currently queued or processing",
)
CIRCUIT_BREAKER_STATE = Gauge(
    "image_intel_circuit_breaker_state",
    "Circuit breaker state per analyzer (0=closed, 1=half-open, 2=open)",
    ["analyzer"],
)
WEBHOOK_DELIVERY_TOTAL = Counter(
    "image_intel_webhook_delivery_total",
    "Total webhook deliveries by status",
    ["status"],
)
UPLOADS_BY_STATUS_MIME_TOTAL = Counter(
    "image_intel_uploads_total",
    "Upload attempts by status and detected mime",
    ["status", "mime"],
)


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


async def track_http_metrics(request: Request, call_next: Callable) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start

    method = request.method
    path = request.url.path
    status = str(response.status_code)

    HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=status).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(elapsed)
    return response


def set_queue_depth(queue_name: str, depth: int) -> None:
    QUEUE_DEPTH.labels(queue=queue_name).set(max(depth, 0))


def refresh_jobs_in_flight() -> None:
    session = get_session()
    try:
        count = (
            session.query(Job)
            .filter(Job.status.in_(("queued", "processing")))
            .count()
        )
        JOBS_IN_FLIGHT.set(float(count))
    finally:
        session.close()
