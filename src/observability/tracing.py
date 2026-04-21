from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request, Response


async def attach_trace_id(request: Request, call_next: Callable) -> Response:
    trace_id = request.headers.get("X-Request-ID") or f"trc_{uuid.uuid4().hex[:24]}"
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = trace_id
    return response
