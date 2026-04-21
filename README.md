# Image Insight

Current build includes Day 1-4 backend features with a working runtime path:
- Authenticated upload endpoint (`Bearer API_KEY`)
- Async job processing (`inmemory` queue now, `rq` seam implemented)
- Retry endpoint for failed jobs
- Local webhook callback dispatch
- Readiness checks with dependency breakdown
- Object store seam (`local` now, `minio` seam implemented)
- Day 5 frontend pages (upload, job status, report view/download)
- Recent uploads panel on the upload screen (backed by cursor endpoint)

## Prereqs
- Python 3.11+
- Docker Desktop (primary intended runtime)
- WeasyPrint native deps (for upcoming PDF work):
  - `brew install pango cairo gdk-pixbuf libffi`

## Quickstart (lite)
```bash
cp .env.example .env
# regenerate API key
openssl rand -hex 32
# set API_KEY in .env

make demo-lite
```

Frontend UI: `http://localhost:5173`


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

## Frontend pages
- `/` Upload page (file + optional webhook URL)
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

## Provider switch (documented)
Default in `.env.example`:
- `AI_PROVIDER=mock`

Planned Claude path:
- `AI_PROVIDER=claude`
- `ANTHROPIC_API_KEY=<your_key>`

See [trade-offs doc](docs/trade-offs.md) for rationale.
