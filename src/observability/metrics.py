from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

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
