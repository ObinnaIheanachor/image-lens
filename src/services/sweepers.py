from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog

from src.config import settings
from src.db.models import Job, Report
from src.db.session import get_session
from src.storage.factory import create_object_store


logger = structlog.get_logger("sweepers")
_store = create_object_store()


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def run_stuck_job_reconciler(*, now: datetime | None = None) -> int:
    reference = now or datetime.now(UTC)
    cutoff = reference - timedelta(seconds=settings.stuck_job_timeout_seconds)

    session = get_session()
    updated = 0
    try:
        candidates = session.query(Job).filter(Job.status == "processing").all()
        stuck_jobs = [job for job in candidates if _to_utc(job.updated_at) < cutoff]
        for job in stuck_jobs:
            job.status = "failed"
            job.error_code = "stuck_job_timeout"
            job.error_message = "Marked failed by reconciler"
            updated += 1
        if updated:
            session.commit()
        return updated
    finally:
        session.close()


def run_retention_sweeper(*, now: datetime | None = None) -> int:
    reference = now or datetime.now(UTC)
    cutoff = reference - timedelta(days=settings.retention_hard_delete_days)

    session = get_session()
    deleted = 0
    try:
        candidates = session.query(Job).filter(Job.status == "deleted").all()
        jobs = [job for job in candidates if _to_utc(job.updated_at) < cutoff]

        for job in jobs:
            try:
                _store.delete(job.image_path)
            except Exception:
                # Best effort; continue cleanup.
                pass

            if job.report_id:
                report = session.get(Report, job.report_id)
                if report:
                    session.delete(report)
            session.delete(job)
            deleted += 1

        if deleted:
            session.commit()
        return deleted
    finally:
        session.close()


async def sweeper_loop(stop_event: asyncio.Event) -> None:
    interval = max(settings.sweep_interval_seconds, 5)
    while not stop_event.is_set():
        try:
            stuck_count = await asyncio.to_thread(run_stuck_job_reconciler)
            retention_count = await asyncio.to_thread(run_retention_sweeper)
            if stuck_count or retention_count:
                logger.info(
                    "sweeper_tick",
                    stuck_jobs_reconciled=stuck_count,
                    retention_deleted=retention_count,
                )
        except Exception as exc:
            logger.warning("sweeper_tick_failed", error=str(exc))

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
