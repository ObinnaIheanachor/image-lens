# Architecture

## Runtime topology

```text
Browser (React/Vite)
  -> FastAPI API (/api/v1/*)
      -> Postgres (jobs/reports)
      -> Redis (RQ queue)
      -> Object store (Local or MinIO)
  -> RQ worker (python -m src.worker)
      -> loads image bytes
      -> runs analyzer
      -> writes report
      -> dispatches webhook
```

## Key module boundaries

- API routes: `src/api/routes.py`
- Queue seam: `src/queue/factory.py`, `src/queue/in_memory.py`, `src/queue/rq_queue.py`
- Storage seam: `src/storage/factory.py`, `src/storage/local.py`, `src/storage/minio_store.py`
- Worker pipeline: `src/services/analysis.py`
- Report rendering: `src/reports/renderer.py`, `src/reports/templates/*`
- Auth: `src/security/auth.py`
- Observability: `src/observability/metrics.py`

## Core flow

1. Upload request hits `POST /api/v1/uploads`.
2. File is validated via magic-byte and decode checks (JPEG/PNG/WebP/HEIC) and stored via object-store abstraction.
3. Job is persisted (`jobs` table) and queued.
4. Worker processes job, writes report (`reports` table).
5. Client polls `GET /jobs/{id}` until done.
6. Client fetches report in JSON/MD/HTML/PDF.
7. Optional webhook POST fires on completion.

## Reliability and correctness features

- Durable state in Postgres for jobs/reports.
- Retry endpoint with attempt cap.
- Idempotency key for single-file upload dedupe semantics.
- Batch upload support (up to 5 files).
- Readiness probe with dependency-level status.
- Prometheus metrics endpoint.

## Deployment modes

- Full stack: `docker compose up --build`
  - Postgres + Redis + MinIO + API + worker + frontend + webhook-echo
- Lite/offline: `docker compose -f docker-compose.lite.yml up --build`
  - API + frontend + webhook-echo using sqlite/local storage/in-memory queue
