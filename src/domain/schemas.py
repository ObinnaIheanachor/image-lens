from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: str
    status: str
    status_url: str
    created_at: datetime


class JobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "done", "failed"]
    attempt_count: int
    report_id: str | None = None
    report_url: str | None = None
    error: dict[str, str] | None = None
    created_at: datetime
    updated_at: datetime


class AnalysisResult(BaseModel):
    summary: str
    tags: list[str]
    confidence: float
    analyzer_version: str


class ReportResponse(BaseModel):
    report_id: str
    job_id: str
    result: AnalysisResult
    created_at: datetime
