from __future__ import annotations

import json
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from src.db.models import Job, Report
from src.db.session import db_ready, get_session
from src.domain.schemas import JobResponse, ReportResponse, UploadResponse
from src.queue.factory import create_queue
from src.security.auth import require_api_key
from src.services.ids import new_job_id
from src.services.webhook_dispatcher import is_valid_webhook_url
from src.storage.factory import create_object_store


router = APIRouter(prefix="/api/v1")
store = create_object_store()
queue_backend = create_queue()


def _validate_jpeg(image_bytes: bytes) -> None:
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="empty_file")
    try:
        img = Image.open(BytesIO(image_bytes))
        img.verify()
        if img.format != "JPEG":
            raise HTTPException(status_code=400, detail="unsupported_media_type")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=422, detail="image_decode_failed") from exc


@router.post("/uploads", response_model=UploadResponse, status_code=202, dependencies=[Depends(require_api_key)])
async def upload(
    file: UploadFile = File(...),
    webhook_url: str | None = Form(default=None),
    metadata: str | None = Form(default=None),
) -> UploadResponse:
    image_bytes = await file.read()
    _validate_jpeg(image_bytes)

    if webhook_url and not is_valid_webhook_url(webhook_url):
        raise HTTPException(status_code=400, detail="invalid_webhook_url")

    if metadata:
        try:
            json.loads(metadata)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid_metadata") from exc

    sha256, image_path = store.put(image_bytes, suffix=".jpg")

    job = Job(
        id=new_job_id(),
        status="queued",
        image_path=image_path,
        image_sha256=sha256,
        image_mime="image/jpeg",
        webhook_url=webhook_url,
        user_metadata_json=metadata,
        attempt_count=0,
    )

    session = get_session()
    try:
        session.add(job)
        session.commit()
        queue_backend.enqueue(job.id)
        session.refresh(job)
        return UploadResponse(
            job_id=job.id,
            status=job.status,
            status_url=f"/api/v1/jobs/{job.id}",
            created_at=job.created_at,
        )
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


@router.get("/reports/{report_id}", response_model=ReportResponse, dependencies=[Depends(require_api_key)])
def get_report(report_id: str) -> ReportResponse:
    session = get_session()
    try:
        report = session.get(Report, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="report_not_found")
        payload = json.loads(report.payload_json)
        return ReportResponse(
            report_id=report.id,
            job_id=report.job_id,
            result=payload,
            created_at=report.created_at,
        )
    finally:
        session.close()


@router.delete("/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def delete_job(job_id: str) -> dict[str, str]:
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job_not_found")
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
