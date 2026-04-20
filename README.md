# Image Insight

Day 1-2 vertical slice implementation:
- `POST /api/v1/uploads` accepts a JPEG and returns `202` with a `job_id`
- Background processor asynchronously runs deterministic mock analysis
- `GET /api/v1/jobs/{job_id}` shows `queued -> processing -> done | failed`
- `GET /api/v1/reports/{report_id}` returns structured JSON report

## Prereqs
- Python 3.11+
- Docker Desktop (primary run path)
- WeasyPrint native deps (required when PDF feature is added):
  - `brew install pango cairo gdk-pixbuf libffi`

## Quickstart (vertical slice)
```bash
cp .env.example .env
make demo-lite
```

API base URL: `http://localhost:${API_PORT:-8000}`

## Curl flow
```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -F "file=@tests/fixtures/valid.jpg"

curl -s http://localhost:8000/api/v1/jobs/<job_id>

curl -s http://localhost:8000/api/v1/reports/<report_id>
```

## Provider switch (planned and documented now)
Default in `.env.example` is:
- `AI_PROVIDER=mock`

To flip later:
- `AI_PROVIDER=claude`
- `ANTHROPIC_API_KEY=<your_key>`

## Acceptance Criteria Progress (live)
Implemented in this slice:
- #3 valid upload returns `job_id` quickly (targeted)
- #4 mock flow reaches `done` and report retrieval works in JSON
- #12 mock provider default (offline-friendly)
- #20 OpenAPI available at `/docs`

Intentionally deferred to next phases:
- #1 full docker-compose stack (Postgres/Redis/MinIO/worker/frontend)
- #2 lite profile parity requirements finalization
- #5 markdown/html/pdf report formats
- #6 idempotency key behavior
- #7/#8/#9 stricter validation/error matrix
- #10 batch upload of 5
- #11 Claude invalid-key failure surfacing
- #13 retry endpoint
- #14 GDPR delete behavior
- #15 webhook delivery
- #16 readiness dependency degradation checks
- #17 Prometheus metrics set
- #18/#19 full tests + lint/types/coverage + CI green
- #21 object-store swap demo path
