from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


def _problem_payload(request: Request, status: int, detail: str, code: str) -> dict:
    trace_id = getattr(request.state, "trace_id", "")
    return {
        "type": "about:blank",
        "title": code,
        "status": status,
        "detail": detail,
        "instance": str(request.url.path),
        "code": code,
        "trace_id": trace_id,
    }


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    code = detail if isinstance(detail, str) else "http_error"
    payload = _problem_payload(request, exc.status_code, str(detail), code)
    return JSONResponse(status_code=exc.status_code, content=payload)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    payload = _problem_payload(request, 500, str(exc), "internal_error")
    return JSONResponse(status_code=500, content=payload)
