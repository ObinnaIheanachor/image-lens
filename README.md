# Image Insight

Production-shaped demo build of the Image Intelligence service.

Status: ready for end-to-end demo on `main`.

Implemented:
- Authenticated upload API (`Authorization: Bearer <API_KEY>`)
- Async processing with worker queue (`rq` in full stack, `inmemory` in lite)
- Analyzer providers: `mock` (default) and `claude`
- Report formats: JSON, Markdown, HTML, PDF
- Idempotency key support + batch upload (up to 5 images)
- Retry endpoint for failed jobs
- Webhook delivery on job completion
- GDPR delete semantics (`DELETE /jobs/{id}`)
- Prometheus metrics + readiness/liveness endpoints
- Structlog JSON request logging + trace IDs
- Operational sweepers (stuck-job reconciler + retention hard-delete)
- Frontend pages: upload, status polling, report view/download, recent uploads

## Prereqs
- Python 3.11+
- Docker Desktop (primary intended runtime)
- WeasyPrint native deps:
  - `brew install pango cairo gdk-pixbuf libffi`

## Quickstart (full stack)
```bash
cp .env.example .env

# regenerate API key (recommended)
openssl rand -hex 32
# set API_KEY in .env

docker compose up -d --build
```

Frontend: `http://localhost:5173`  
API docs: `http://localhost:8000/docs`

## Quickstart (offline lite fallback)
```bash
cp .env.example .env
make demo-lite
```

Default UI is end-user mode (no API key or webhook fields shown).
Developer/operator controls are available only with `?mode=dev`, for example:
- `http://localhost:5173/?mode=dev`

## API auth
All core endpoints require:
```http
Authorization: Bearer <API_KEY>
```

The frontend prompts for API key and stores it in `sessionStorage` for the current tab.

## Database migrations (Alembic)
Schema lifecycle is migration-driven for Postgres.

Compose runs migrations automatically before API startup:
- `alembic upgrade head && uvicorn ...`

Manual commands:
```bash
make migrate-up
make migrate-current
```

## Provider mode
Default in `.env.example`:
- `AI_PROVIDER=mock`

To run real model path:
```bash
# in .env
AI_PROVIDER=claude
ANTHROPIC_API_KEY=<your_key>
```

Then recreate API + worker:
```bash
docker compose up -d --build --force-recreate api worker
```

## Frontend pages
- `/` Upload page (supports JPEG/PNG/WebP/HEIC)
- `/` optional webhook field in `?mode=dev`
- `/` includes a recent uploads panel (latest completed jobs/reports)
- `/jobs/:jobId` Status polling page with retry action
- `/reports/:reportId` Report page with:
  - HTML preview
  - Download JSON
  - Download Markdown
  - Download PDF

## Core flow (curl)
```bash
API_KEY=$(grep '^API_KEY=' .env | cut -d= -f2)

curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@tests/fixtures/valid.jpg"

curl -s http://localhost:8000/api/v1/jobs/<job_id> \
  -H "Authorization: Bearer $API_KEY"

curl -s http://localhost:8000/api/v1/reports/<report_id> \
  -H "Authorization: Bearer $API_KEY"

# report formats
curl -s http://localhost:8000/api/v1/reports/<report_id> \
  -H "Authorization: Bearer $API_KEY" \
  -H "Accept: text/markdown"

curl -s http://localhost:8000/api/v1/reports/<report_id> \
  -H "Authorization: Bearer $API_KEY" \
  -H "Accept: text/html"

curl -s http://localhost:8000/api/v1/reports/<report_id> \
  -H "Authorization: Bearer $API_KEY" \
  -H "Accept: application/pdf" \
  -o report.pdf
```

## Retry flow test
```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@tests/fixtures/valid.jpg" \
  -F 'metadata={"force_fail_once":true}'

curl -s -X POST http://localhost:8000/api/v1/jobs/<job_id>/retry \
  -H "Authorization: Bearer $API_KEY"
```

## Webhook test (offline)
Use local echo service in compose:
- `http://webhook-echo:8080` from containers
- `http://localhost:${WEBHOOK_ECHO_PORT:-8888}` from host

Upload with:
```bash
-F "webhook_url=http://localhost:8888/hook"
```

## Readiness
- `GET /api/v1/healthz` -> liveness
- `GET /api/v1/readyz` -> dependency status; returns `503` when degraded

## Runtime hardening
- Upload rate limiting is enabled by default (`RATE_LIMIT_ENABLED=true`) and uses Redis when available.
- Structured JSON logging is enabled via `structlog` for request/access logs.
- Operational sweepers run as background tasks:
  - stuck-job reconciler (`STUCK_JOB_TIMEOUT_SECONDS`)
  - retention hard-delete sweeper (`RETENTION_HARD_DELETE_DAYS`)

## Validation commands
```bash
python3.11 -m ruff check .
python3.11 -m mypy src tests
python3.11 -m pytest -q tests

# critical-module coverage gate
python3.11 -m pytest -q tests -o addopts='' \
  --cov=src/services \
  --cov=src/security \
  --cov=src/analyzers \
  --cov=src/reports \
  --cov-fail-under=80
```

See supporting docs:
- [API reference](docs/api.md)
- [Architecture](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [Acceptance checklist](docs/acceptance-checklist.md)
- [Interview script](docs/interview-script.md)
- [Trade-offs](docs/trade-offs.md)
