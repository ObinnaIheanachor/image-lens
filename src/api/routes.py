from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

from src.config import settings
from src.db.models import Job, Report
from src.db.session import db_ready, get_session
from src.domain.errors import ValidationError
from src.domain.schemas import JobResponse, ReportResponse, UploadResponse
from src.observability.metrics import JOBS_RETRY_TOTAL, UPLOADS_TOTAL, metrics_response
from src.queue.factory import create_queue
from src.reports.renderer import render_html, render_markdown, render_pdf
from src.security.auth import require_api_key
from src.security.validation import validate_image_bytes
from src.services.ids import new_job_id
from src.services.webhook_dispatcher import is_valid_webhook_url
from src.storage.factory import create_object_store


router = APIRouter(prefix="/api/v1")
store = create_object_store()
queue_backend = create_queue()


@router.post(
    "/uploads",
    response_model=UploadResponse | list[UploadResponse],
    status_code=202,
    dependencies=[Depends(require_api_key)],
)
async def upload(
    file: UploadFile | None = File(default=None),
    files: list[UploadFile] | None = File(default=None, alias="files[]"),
    files_alt: list[UploadFile] | None = File(default=None, alias="files"),
    webhook_url: str | None = Form(default=None),
    metadata: str | None = Form(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> UploadResponse | list[UploadResponse]:
    upload_files: list[UploadFile] = []
    if file is not None:
        upload_files.append(file)
    if files:
        upload_files.extend(files)
    if files_alt:
        upload_files.extend(files_alt)

    if not upload_files:
        raise HTTPException(status_code=400, detail="empty_file")
    if len(upload_files) > 5:
        raise HTTPException(status_code=400, detail="too_many_files")
    UPLOADS_TOTAL.labels(mode="batch" if len(upload_files) > 1 else "single").inc()
    if idempotency_key and len(upload_files) > 1:
        raise HTTPException(status_code=400, detail="idempotency_not_supported_for_batch")

    if webhook_url and not is_valid_webhook_url(webhook_url):
        raise HTTPException(status_code=400, detail="invalid_webhook_url")

    if metadata:
        try:
            json.loads(metadata)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid_metadata") from exc

    session = get_session()
    try:
        responses: list[UploadResponse] = []

        for index, upload_file in enumerate(upload_files):
            image_bytes = await upload_file.read()
            try:
                validated = validate_image_bytes(
                    image_bytes,
                    max_size_bytes=settings.max_upload_size_bytes,
                    max_width=settings.max_image_width,
                    max_height=settings.max_image_height,
                )
            except ValidationError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

            sha256, image_path = store.put(image_bytes, suffix=validated.suffix)

            file_idempotency_key = idempotency_key if index == 0 else None
            enqueue_job = True

            if file_idempotency_key:
                existing_job = (
                    session.query(Job)
                    .filter(Job.idempotency_key == file_idempotency_key)
                    .order_by(Job.created_at.desc())
                    .first()
                )
                if existing_job:
                    if existing_job.image_sha256 != sha256:
                        raise HTTPException(status_code=409, detail="idempotency_conflict")
                    job = existing_job
                    enqueue_job = False
                else:
                    job = Job(
                        id=new_job_id(),
                        status="queued",
                        image_path=image_path,
                        image_sha256=sha256,
                        image_mime=validated.mime,
                        image_bytes=validated.size_bytes,
                        image_width=validated.width,
                        image_height=validated.height,
                        idempotency_key=file_idempotency_key,
                        webhook_url=webhook_url,
                        user_metadata_json=metadata,
                        attempt_count=0,
                    )
                    session.add(job)
                    session.commit()
                    session.refresh(job)
            else:
                job = Job(
                    id=new_job_id(),
                    status="queued",
                    image_path=image_path,
                    image_sha256=sha256,
                    image_mime=validated.mime,
                    image_bytes=validated.size_bytes,
                    image_width=validated.width,
                    image_height=validated.height,
                    idempotency_key=None,
                    webhook_url=webhook_url,
                    user_metadata_json=metadata,
                    attempt_count=0,
                )
                session.add(job)
                session.commit()
                session.refresh(job)

            if enqueue_job:
                queue_backend.enqueue(job.id)

            responses.append(
                UploadResponse(
                    job_id=job.id,
                    status=job.status,
                    status_url=f"/api/v1/jobs/{job.id}",
                    created_at=job.created_at,
                )
            )

        if len(responses) == 1:
            return responses[0]
        return responses
    finally:
        session.close()


@router.get("/jobs/{job_id}", response_model=JobResponse, dependencies=[Depends(require_api_key)])
def get_job(job_id: str) -> JobResponse:
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job_not_found")
        return JobResponse(
            job_id=job.id,
            status=job.status,
            attempt_count=job.attempt_count,
            report_id=job.report_id,
            report_url=f"/api/v1/reports/{job.report_id}" if job.report_id else None,
            error={"code": job.error_code, "message": job.error_message}
            if job.error_code
            else None,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
    finally:
        session.close()


@router.post("/jobs/{job_id}/retry", response_model=JobResponse, dependencies=[Depends(require_api_key)])
def retry_job(job_id: str) -> JobResponse:
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job_not_found")
        if job.status != "failed":
            raise HTTPException(status_code=400, detail="job_not_failed")
        if job.attempt_count >= 3:
            raise HTTPException(status_code=400, detail="retry_limit_exceeded")

        job.status = "queued"
        job.error_code = None
        job.error_message = None
        session.commit()
        JOBS_RETRY_TOTAL.inc()
        queue_backend.enqueue(job.id)
        session.refresh(job)

        return JobResponse(
            job_id=job.id,
            status=job.status,
            attempt_count=job.attempt_count,
            report_id=job.report_id,
            report_url=f"/api/v1/reports/{job.report_id}" if job.report_id else None,
            error=None,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
    finally:
        session.close()


@router.get("/reports/{report_id}", dependencies=[Depends(require_api_key)])
def get_report(report_id: str, accept: str | None = Header(default="application/json")) -> Response:
    session = get_session()
    try:
        report = session.get(Report, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="report_not_found")
        job = session.get(Job, report.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job_not_found")

        if not report.payload_json:
            raise HTTPException(status_code=410, detail="report_deleted")
        payload = json.loads(report.payload_json)
        report_json = ReportResponse(
            report_id=report.id,
            job_id=report.job_id,
            result=payload,
            created_at=report.created_at,
        ).model_dump(mode="json")

        context = {
            "report_id": report.id,
            "job_id": report.job_id,
            "generated_at": report.created_at.isoformat(),
            "image_sha256": job.image_sha256,
            "analyzer_version": payload.get("analyzer_version", "unknown"),
            "summary": payload.get("summary", ""),
            "tags": payload.get("tags", []),
            "confidence": payload.get("confidence", ""),
        }

        accepts = (accept or "application/json").lower()
        if "application/pdf" in accepts:
            try:
                pdf_bytes = render_pdf(context)
            except RuntimeError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{report.id}.pdf"',
                },
            )
        if "text/html" in accepts:
            return HTMLResponse(content=render_html(context))
        if "text/markdown" in accepts:
            return PlainTextResponse(content=render_markdown(context), media_type="text/markdown")
        return JSONResponse(content=report_json, media_type="application/json")
    finally:
        session.close()


@router.delete("/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def delete_job(job_id: str) -> dict[str, str]:
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job_not_found")

        try:
            store.delete(job.image_path)
        except Exception:
            # Best-effort delete while preserving request semantics.
            pass

        if job.report_id:
            report = session.get(Report, job.report_id)
            if report:
                report.payload_json = None

        job.status = "deleted"
        session.commit()
        return {"status": "deleted", "job_id": job.id}
    finally:
        session.close()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> tuple[dict, int] | dict:
    queue_ok = queue_backend.is_ready()
    store_ok = store.ready()
    db_ok = db_ready()

    payload = {
        "status": "ok" if (queue_ok and store_ok and db_ok) else "degraded",
        "dependencies": {
            "database": "ok" if db_ok else "down",
            "queue": "ok" if queue_ok else "down",
            "object_store": "ok" if store_ok else "down",
        },
    }

    if payload["status"] == "ok":
        return payload
    raise HTTPException(status_code=503, detail=payload)


@router.get("/metrics")
def metrics() -> Response:
    return metrics_response()


@router.get("/reports", dependencies=[Depends(require_api_key)])
def list_reports(limit: int = 20, cursor: str | None = None) -> dict:
    session = get_session()
    try:
        safe_limit = min(max(limit, 1), 100)
        query = session.query(Job).filter(Job.report_id.isnot(None)).order_by(Job.created_at.desc())
        if cursor:
            try:
                cursor_dt = datetime.fromisoformat(cursor)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="invalid_cursor") from exc
            query = query.filter(Job.created_at < cursor_dt)

        rows = query.limit(safe_limit + 1).all()
        has_more = len(rows) > safe_limit
        rows = rows[:safe_limit]

        items = [
            {
                "job_id": r.id,
                "status": r.status,
                "report_id": r.report_id,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rows
        ]
        next_cursor = rows[-1].created_at.isoformat() if has_more and rows else None
        return {"items": items, "next_cursor": next_cursor}
    finally:
        session.close()
