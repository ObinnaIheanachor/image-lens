from __future__ import annotations

import json
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from src.db.models import Job, Report
from src.db.session import get_session
from src.domain.schemas import JobResponse, ReportResponse, UploadResponse
from src.services.ids import new_job_id
from src.services.processor import processor
from src.storage.local import LocalStore


router = APIRouter(prefix="/api/v1")
store = LocalStore()


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


@router.post("/uploads", response_model=UploadResponse, status_code=202)
async def upload(file: UploadFile = File(...)) -> UploadResponse:
    image_bytes = await file.read()
    _validate_jpeg(image_bytes)
    sha256, image_path = store.put(image_bytes, suffix=".jpg")

    job = Job(
        id=new_job_id(),
        status="queued",
        image_path=image_path,
        image_sha256=sha256,
        image_mime="image/jpeg",
        attempt_count=0,
    )

    session = get_session()
    try:
        session.add(job)
        session.commit()
        processor.enqueue(job.id)
        session.refresh(job)
        return UploadResponse(
            job_id=job.id,
            status=job.status,
            status_url=f"/api/v1/jobs/{job.id}",
            created_at=job.created_at,
        )
    finally:
        session.close()


@router.get("/jobs/{job_id}", response_model=JobResponse)
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


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: str) -> ReportResponse:
    session = get_session()
    try:
        report = session.get(Report, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="report_not_found")
        payload = json.loads(report.payload_json)
        return ReportResponse(report_id=report.id, job_id=report.job_id, result=payload, created_at=report.created_at)
    finally:
        session.close()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
